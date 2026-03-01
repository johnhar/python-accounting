import pytest
from sqlalchemy import select
from python_accounting.models import Entity
from python_accounting.models.fund import Fund
from python_accounting.exceptions import HangingTransactionsError


def test_fund_crud(session, entity):
    """Tests CRUD operations for the Fund model"""
    fund = Fund(name="general fund", entity_id=entity.id)
    session.add(fund)
    session.commit()

    fund = session.get(Fund, fund.id)
    assert fund.name == "General Fund"  # title-cased by validate()
    assert fund.entity_id == entity.id


def test_fund_with_code_and_description(session, entity):
    """Tests Fund with optional fields"""
    fund = Fund(
        name="building fund",
        description="For the new building",
        fund_code="BF001",
        entity_id=entity.id,
    )
    session.add(fund)
    session.commit()

    fund = session.get(Fund, fund.id)
    assert fund.description == "For the new building"
    assert fund.fund_code == "BF001"


def test_fund_name_required(session, entity):
    """Tests that fund name is required"""
    fund = Fund(name="", entity_id=entity.id)
    with pytest.raises(ValueError):
        session.add(fund)
        session.commit()


def test_fund_recycling(session, entity):
    """Tests soft delete, restore, and destroy for the Fund model"""
    fund = Fund(name="Test Fund", entity_id=entity.id)
    session.add(fund)
    session.commit()

    fund_id = fund.id
    session.delete(fund)

    fund = session.get(Fund, fund_id)
    assert fund is None

    fund = session.get(Fund, fund_id, include_deleted=True)
    assert fund is not None
    session.restore(fund)

    fund = session.get(Fund, fund_id)
    assert fund is not None

    session.destroy(fund)
    fund = session.get(Fund, fund_id)
    assert fund is None


def test_fund_entity_isolation(session, entity):
    """Tests that funds are isolated by entity"""
    fund1 = Fund(name="Fund One", entity_id=entity.id)
    session.add(fund1)
    session.commit()

    session.entity = None
    entity2 = Entity(name="Entity Two")
    session.add(entity2)
    session.commit()
    entity2 = session.get(Entity, entity2.id)

    fund2 = Fund(name="Fund Two", entity_id=entity2.id)
    session.add(fund2)
    session.commit()

    # Session is scoped to entity2
    funds = session.scalars(select(Fund)).all()
    assert len(funds) == 1
    assert funds[0].name == "Fund Two"

    # Switch back to entity1
    session.entity = entity
    funds = session.scalars(select(Fund)).all()
    assert len(funds) == 1
    assert funds[0].name == "Fund One"
