import pytest
from sqlalchemy import select
from python_accounting.models import Entity
from python_accounting.models.project import Project
from python_accounting.exceptions import HangingTransactionsError


def test_project_crud(session, entity):
    """Tests CRUD operations for the Project model"""
    project = Project(name="website redesign", entity_id=entity.id)
    session.add(project)
    session.commit()

    project = session.get(Project, project.id)
    assert project.name == "Website Redesign"  # title-cased by validate()
    assert project.entity_id == entity.id


def test_project_with_description(session, entity):
    """Tests Project with optional description"""
    project = Project(
        name="mobile app",
        description="New mobile application",
        entity_id=entity.id,
    )
    session.add(project)
    session.commit()

    project = session.get(Project, project.id)
    assert project.description == "New mobile application"


def test_project_name_required(session, entity):
    """Tests that project name is required"""
    project = Project(name="", entity_id=entity.id)
    with pytest.raises(ValueError):
        session.add(project)
        session.commit()


def test_project_recycling(session, entity):
    """Tests soft delete, restore, and destroy for the Project model"""
    project = Project(name="Test Project", entity_id=entity.id)
    session.add(project)
    session.commit()

    project_id = project.id
    session.delete(project)

    project = session.get(Project, project_id)
    assert project is None

    project = session.get(Project, project_id, include_deleted=True)
    assert project is not None
    session.restore(project)

    project = session.get(Project, project_id)
    assert project is not None
