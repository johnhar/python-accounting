import pytest
from sqlalchemy import select
from python_accounting.models import Entity
from python_accounting.models.team import Team
from python_accounting.exceptions import HangingTransactionsError


def test_team_crud(session, entity):
    """Tests CRUD operations for the Team model"""
    team = Team(name="engineering", entity_id=entity.id)
    session.add(team)
    session.commit()

    team = session.get(Team, team.id)
    assert team.name == "Engineering"  # title-cased by validate()
    assert team.entity_id == entity.id


def test_team_with_description(session, entity):
    """Tests Team with optional description"""
    team = Team(
        name="marketing",
        description="Marketing department",
        entity_id=entity.id,
    )
    session.add(team)
    session.commit()

    team = session.get(Team, team.id)
    assert team.description == "Marketing department"


def test_team_name_required(session, entity):
    """Tests that team name is required"""
    team = Team(name="", entity_id=entity.id)
    with pytest.raises(ValueError):
        session.add(team)
        session.commit()


def test_team_recycling(session, entity):
    """Tests soft delete, restore, and destroy for the Team model"""
    team = Team(name="Test Team", entity_id=entity.id)
    session.add(team)
    session.commit()

    team_id = team.id
    session.delete(team)

    team = session.get(Team, team_id)
    assert team is None

    team = session.get(Team, team_id, include_deleted=True)
    assert team is not None
    session.restore(team)

    team = session.get(Team, team_id)
    assert team is not None
