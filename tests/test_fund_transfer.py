import pytest
from datetime import datetime
from python_accounting.models import Entity, Account, Currency, LineItem, Balance, Ledger
from python_accounting.models.fund import Fund
from python_accounting.transactions.fund_transfer import FundTransfer
from python_accounting.exceptions import (
    FundAccountingDisabledError,
    MissingFundError,
    SameFundTransferError,
    InvalidTaxChargeError,
)


def _setup_fund_entity(session):
    """Helper to create a fund accounting entity with currency"""
    entity = Entity(name="Fund Transfer Test Entity", fund_accounting=True)
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


def test_fund_transfer_logical(session):
    """Tests logical fund transfer (same account, different funds)"""
    entity, currency = _setup_fund_entity(session)

    fund1 = Fund(name="General Fund", entity_id=entity.id)
    fund2 = Fund(name="Building Fund", entity_id=entity.id)
    session.add_all([fund1, fund2])
    session.commit()

    bank = Account(
        name="Main Bank",
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

    transaction = FundTransfer(
        narration="Transfer from General to Building Fund",
        transaction_date=datetime.now(),
        account_id=bank.id,
        fund_id=fund1.id,  # source fund
        entity_id=entity.id,
    )
    session.add(transaction)
    session.commit()

    line_item = LineItem(
        narration="Building fund allocation",
        account_id=revenue.id,
        amount=500,
        fund_id=fund2.id,  # destination fund
        entity_id=entity.id,
    )
    session.add(line_item)
    session.flush()

    transaction.line_items.add(line_item)
    session.add(transaction)
    session.flush()

    transaction.post(session)

    # Verify ledger entries have different fund_ids
    ledgers = transaction.ledgers
    assert len(ledgers) == 2

    post_ledger = [l for l in ledgers if l.entry_type == Balance.BalanceType.DEBIT][0]
    folio_ledger = [l for l in ledgers if l.entry_type == Balance.BalanceType.CREDIT][0]

    assert post_ledger.fund_id == fund1.id  # source fund
    assert folio_ledger.fund_id == fund2.id  # destination fund


def test_fund_transfer_requires_fund_accounting(session, entity, currency):
    """Tests that fund transfer requires fund_accounting=True"""
    bank = Account(
        name="Bank",
        account_type=Account.AccountType.BANK,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    session.add(bank)
    session.flush()

    transaction = FundTransfer(
        narration="Test transfer",
        transaction_date=datetime.now(),
        account_id=bank.id,
        entity_id=entity.id,
    )
    session.add(transaction)

    with pytest.raises(FundAccountingDisabledError):
        session.commit()


def test_fund_transfer_requires_source_fund(session):
    """Tests that fund transfer requires a source fund"""
    entity, currency = _setup_fund_entity(session)

    bank = Account(
        name="Bank",
        account_type=Account.AccountType.BANK,
        currency_id=currency.id,
        entity_id=entity.id,
    )
    session.add(bank)
    session.flush()

    transaction = FundTransfer(
        narration="Test transfer",
        transaction_date=datetime.now(),
        account_id=bank.id,
        entity_id=entity.id,
        # No fund_id — should fail
    )
    session.add(transaction)

    with pytest.raises(MissingFundError):
        session.commit()


def test_fund_transfer_same_fund_error(session):
    """Tests that source and destination funds must differ"""
    entity, currency = _setup_fund_entity(session)

    fund1 = Fund(name="General Fund", entity_id=entity.id)
    session.add(fund1)
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

    transaction = FundTransfer(
        narration="Same fund transfer",
        transaction_date=datetime.now(),
        account_id=bank.id,
        fund_id=fund1.id,
        entity_id=entity.id,
    )
    session.add(transaction)
    session.commit()

    line_item = LineItem(
        narration="Same fund line item",
        account_id=revenue.id,
        amount=100,
        fund_id=fund1.id,  # Same as source — should fail
        entity_id=entity.id,
    )
    session.add(line_item)
    session.flush()

    transaction.line_items.add(line_item)
    session.add(transaction)

    with pytest.raises(SameFundTransferError):
        session.commit()
