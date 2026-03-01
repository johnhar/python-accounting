import pytest
from sqlalchemy import create_engine
from python_accounting.models import Entity, Base, Currency
from python_accounting.models.fund import Fund
from python_accounting.models.team import Team
from python_accounting.models.project import Project
from python_accounting.database.session import get_session
from python_accounting.config import config


@pytest.fixture
def engine():
    database = config.database
    engine = create_engine(database["url"], echo=database["echo"])
    Base.metadata.create_all(engine)
    return engine


@pytest.fixture
def session(engine):
    with get_session(engine) as session:
        yield session


@pytest.fixture
def entity(session):
    entity = Entity(name="Test Entity")
    session.add(entity)
    session.commit()
    return session.get(Entity, entity.id)


@pytest.fixture
def currency(session, entity):
    currency = Currency(name="US Dollars", code="USD", entity_id=entity.id)
    session.add(currency)
    session.commit()
    return session.get(Currency, currency.id)


@pytest.fixture
def fund(session, entity):
    fund = Fund(name="General Fund", entity_id=entity.id)
    session.add(fund)
    session.commit()
    return session.get(Fund, fund.id)


@pytest.fixture
def team(session, entity):
    team = Team(name="Engineering", entity_id=entity.id)
    session.add(team)
    session.commit()
    return session.get(Team, team.id)


@pytest.fixture
def project(session, entity):
    project = Project(name="Main Project", entity_id=entity.id)
    session.add(project)
    session.commit()
    return session.get(Project, project.id)


@pytest.fixture
def fund_entity(session):
    """Entity with fund_accounting=True"""
    entity = Entity(name="Fund Test Entity", fund_accounting=True)
    session.add(entity)
    session.commit()
    return session.get(Entity, entity.id)
