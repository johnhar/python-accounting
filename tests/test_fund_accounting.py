import pytest
from datetime import datetime
from python_accounting.models import Entity, Account, Currency, LineItem, Balance
from python_accounting.models.fund import Fund
from python_accounting.transactions import CashSale
from python_accounting.exceptions import (
    ImmutableFieldError,
    MissingFundError,
    MixedFundError,
)


def _setup_fund_entity(session):
    """Helper to create a fund accounting entity"""
    entity = Entity(name="Fund Accounting Entity", fund_accounting=True)
    session.add(entity)
    session.commit()
    entity = session.get(Entity, entity.id)

    currency = Currency(name="US Dollars", code="USD", entity_id=entity.id)
    session.add(currency)
    session.commit()

    entity.currency_id = currency.id
    session.commit()
    entity = session.get(Entity, entity.id)

    return entity, currency


def test_fund_accounting_flag_default(session, entity):
    """Tests that fund_accounting defaults to False"""
    assert entity.fund_accounting is False


def test_fund_accounting_flag_enabled(session):
    """Tests that fund_accounting can be set to True"""
    entity = Entity(name="Fund Entity", fund_accounting=True)
    session.add(entity)
    session.commit()

    entity = session.get(Entity, entity.id)
    assert entity.fund_accounting is True


def test_fund_accounting_flag_immutable(session):
    """Tests that fund_accounting cannot be changed after creation"""
    entity = Entity(name="Immutable Entity", fund_accounting=True)
    session.add(entity)
    session.commit()

    entity = session.get(Entity, entity.id)
    entity.fund_accounting = False

    with pytest.raises(ImmutableFieldError) as e:
        session.commit()
    assert "fund_accounting" in str(e.value)


def test_line_item_requires_fund_when_enabled(session):
    """Tests that line items require fund_id when fund accounting is enabled"""
    entity, currency = _setup_fund_entity(session)

    account = Account(
        name="Revenue",
        account_type=Account.AccountType.OPERATING_REVENUE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    session.add(account)
    session.flush()

    line_item = LineItem(
        narration="No fund line item",
        account_id=account.id,
        amount=100,
        entity_id=entity.id,
        # No fund_id — should fail
    )

    with pytest.raises(MissingFundError):
        session.add(line_item)
        session.commit()


def test_line_item_fund_optional_when_disabled(session, entity, currency):
    """Tests that fund_id is optional when fund accounting is disabled"""
    account = Account(
        name="Revenue",
        account_type=Account.AccountType.OPERATING_REVENUE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    session.add(account)
    session.flush()

    line_item = LineItem(
        narration="No fund line item",
        account_id=account.id,
        amount=100,
        entity_id=entity.id,
    )
    session.add(line_item)
    session.commit()
    assert line_item.fund_id is None


def test_mixed_fund_line_items(session):
    """Tests that transactions with fund accounting cannot mix funds in line items"""
    entity, currency = _setup_fund_entity(session)

    fund1 = Fund(name="Fund One", entity_id=entity.id)
    fund2 = Fund(name="Fund Two", entity_id=entity.id)
    session.add_all([fund1, fund2])
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
    revenue2 = Account(
        name="Revenue 2",
        account_type=Account.AccountType.OPERATING_REVENUE,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    session.add_all([bank, revenue, revenue2])
    session.flush()

    transaction = CashSale(
        narration="Mixed fund sale",
        transaction_date=datetime.now(),
        account_id=bank.id,
        entity_id=entity.id,
    )
    session.add(transaction)
    session.commit()

    li1 = LineItem(
        narration="Line 1",
        account_id=revenue.id,
        amount=100,
        fund_id=fund1.id,
        entity_id=entity.id,
    )
    li2 = LineItem(
        narration="Line 2",
        account_id=revenue2.id,
        amount=200,
        fund_id=fund2.id,  # Different fund
        entity_id=entity.id,
    )
    session.add_all([li1, li2])
    session.flush()

    transaction.line_items.add(li1)
    transaction.line_items.add(li2)
    session.add(transaction)

    with pytest.raises(MixedFundError):
        session.commit()


def test_transaction_with_fund(session):
    """Tests that transactions work properly with fund_id set"""
    entity, currency = _setup_fund_entity(session)

    fund = Fund(name="General Fund", entity_id=entity.id)
    session.add(fund)
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

    transaction = CashSale(
        narration="Fund sale",
        transaction_date=datetime.now(),
        account_id=bank.id,
        entity_id=entity.id,
    )
    session.add(transaction)
    session.commit()

    line_item = LineItem(
        narration="Fund line item",
        account_id=revenue.id,
        amount=100,
        fund_id=fund.id,
        entity_id=entity.id,
    )
    session.add(line_item)
    session.flush()

    transaction.line_items.add(line_item)
    session.add(transaction)
    session.flush()

    transaction.post(session)

    # Verify ledger entries have fund_id
    for ledger in transaction.ledgers:
        assert ledger.fund_id == fund.id
