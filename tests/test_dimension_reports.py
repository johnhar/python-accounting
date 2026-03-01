import pytest
from datetime import datetime
from python_accounting.models import Entity, Account, Currency, LineItem, Balance
from python_accounting.models.fund import Fund
from python_accounting.models.team import Team
from python_accounting.models.project import Project
from python_accounting.transactions import CashSale
from python_accounting.reports import IncomeStatement, BalanceSheet, TrialBalance


def _setup_entity_with_dimensions(session):
    """Helper to set up entity with fund, team, project and transactions"""
    entity = Entity(name="Dimension Test Entity", fund_accounting=True)
    session.add(entity)
    session.commit()
    entity = session.get(Entity, entity.id)

    currency = Currency(name="US Dollars", code="USD", entity_id=entity.id)
    session.add(currency)
    session.commit()

    entity.currency_id = currency.id
    session.commit()
    entity = session.get(Entity, entity.id)

    fund1 = Fund(name="General Fund", entity_id=entity.id)
    fund2 = Fund(name="Building Fund", entity_id=entity.id)
    team1 = Team(name="Engineering", entity_id=entity.id)
    team2 = Team(name="Marketing", entity_id=entity.id)
    project1 = Project(name="Project Alpha", entity_id=entity.id)
    session.add_all([fund1, fund2, team1, team2, project1])
    session.commit()

    bank = Account(
        name="Bank",
        account_type=Account.AccountType.BANK,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    revenue = Account(
        name="Revenue",
        account_type=Account.AccountType.OPERATING_REVENUE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    session.add_all([bank, revenue])
    session.flush()

    # Transaction 1: fund1, team1, project1 - amount 100
    tx1 = CashSale(
        narration="Sale one",
        transaction_date=datetime.now(),
        account_id=bank.id,
        entity_id=entity.id,
    )
    session.add(tx1)
    session.commit()

    li1 = LineItem(
        narration="Line item one",
        account_id=revenue.id,
        amount=100,
        fund_id=fund1.id,
        team_id=team1.id,
        project_id=project1.id,
        entity_id=entity.id,
    )
    session.add(li1)
    session.flush()
    tx1.line_items.add(li1)
    session.add(tx1)
    session.flush()
    tx1.post(session)

    # Transaction 2: fund2, team2, no project - amount 200
    tx2 = CashSale(
        narration="Sale two",
        transaction_date=datetime.now(),
        account_id=bank.id,
        entity_id=entity.id,
    )
    session.add(tx2)
    session.commit()

    li2 = LineItem(
        narration="Line item two",
        account_id=revenue.id,
        amount=200,
        fund_id=fund2.id,
        team_id=team2.id,
        entity_id=entity.id,
    )
    session.add(li2)
    session.flush()
    tx2.line_items.add(li2)
    session.add(tx2)
    session.flush()
    tx2.post(session)

    return entity, currency, fund1, fund2, team1, team2, project1, bank, revenue


def test_fund_filtered_income_statement(session):
    """Tests that IncomeStatement can be filtered by fund"""
    entity, currency, fund1, fund2, *_ = _setup_entity_with_dimensions(session)

    # All funds
    report_all = IncomeStatement(session)
    total_rev = report_all.result_amounts[report_all.results.TOTAL_REVENUE.name]
    assert total_rev == 300  # 100 + 200

    # Fund 1 only
    report_f1 = IncomeStatement(session, fund_id=fund1.id)
    rev_f1 = report_f1.result_amounts[report_f1.results.TOTAL_REVENUE.name]
    assert rev_f1 == 100

    # Fund 2 only
    report_f2 = IncomeStatement(session, fund_id=fund2.id)
    rev_f2 = report_f2.result_amounts[report_f2.results.TOTAL_REVENUE.name]
    assert rev_f2 == 200


def test_team_filtered_income_statement(session):
    """Tests that IncomeStatement can be filtered by team"""
    entity, currency, _, _, team1, team2, *_ = _setup_entity_with_dimensions(session)

    report_t1 = IncomeStatement(session, team_id=team1.id)
    rev_t1 = report_t1.result_amounts[report_t1.results.TOTAL_REVENUE.name]
    assert rev_t1 == 100

    report_t2 = IncomeStatement(session, team_id=team2.id)
    rev_t2 = report_t2.result_amounts[report_t2.results.TOTAL_REVENUE.name]
    assert rev_t2 == 200


def test_project_filtered_income_statement(session):
    """Tests that IncomeStatement can be filtered by project"""
    entity, currency, _, _, _, _, project1, *_ = _setup_entity_with_dimensions(session)

    report_p1 = IncomeStatement(session, project_id=project1.id)
    rev_p1 = report_p1.result_amounts[report_p1.results.TOTAL_REVENUE.name]
    assert rev_p1 == 100  # Only tx1 has project1


def test_combined_dimension_filter(session):
    """Tests filtering by multiple dimensions simultaneously"""
    entity, currency, fund1, _, team1, _, project1, *_ = _setup_entity_with_dimensions(session)

    # Fund1 + Team1 — should give 100
    report = IncomeStatement(session, fund_id=fund1.id, team_id=team1.id)
    rev = report.result_amounts[report.results.TOTAL_REVENUE.name]
    assert rev == 100


def test_dimension_orthogonality(session):
    """Tests that filtering by one dimension doesn't affect others"""
    entity, currency, fund1, fund2, team1, team2, project1, bank, revenue = (
        _setup_entity_with_dimensions(session)
    )

    # Filter by team1 — should only get tx1 (fund1), regardless of fund filter
    report_t1 = IncomeStatement(session, team_id=team1.id)
    rev_t1 = report_t1.result_amounts[report_t1.results.TOTAL_REVENUE.name]
    assert rev_t1 == 100

    # Combining fund2 + team1 should give 0 (no transaction matches both)
    report_cross = IncomeStatement(session, fund_id=fund2.id, team_id=team1.id)
    rev_cross = report_cross.result_amounts[report_cross.results.TOTAL_REVENUE.name]
    assert rev_cross == 0
