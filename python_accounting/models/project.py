# models/project.py
# Copyright (C) 2024 - 2028 the PythonAccounting authors and contributors
# <see AUTHORS file>
#
# This module is part of PythonAccounting and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

"""
Represents a Project for dimensional tagging of ledger entries.

"""
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, ForeignKey, func
from python_accounting.mixins import IsolatingMixin
from python_accounting.models import Recyclable
from python_accounting.exceptions import HangingTransactionsError


class Project(IsolatingMixin, Recyclable):
    """Represents a Project for cost/revenue tracking."""

    __mapper_args__ = {"polymorphic_identity": "Project"}

    id: Mapped[int] = mapped_column(ForeignKey("recyclable.id"), primary_key=True)
    """(int): The primary key of the Project database record."""
    name: Mapped[str] = mapped_column(String(255))
    """(str): The name of the Project."""
    description: Mapped[str] = mapped_column(String(1000), nullable=True)
    """(`str`, optional): A description of the Project."""

    def __repr__(self) -> str:
        return self.name

    def validate(self, _) -> None:
        """
        Validates the Project properties.

        Raises:
            ValueError: If the Project name is not provided.

        Returns:
            None
        """
        if not self.name:
            raise ValueError("Project name is required.")
        self.name = self.name.title()

    def validate_delete(self, session) -> None:
        """
        Validates if the Project can be deleted.

        Raises:
            HangingTransactionsError: If any Ledger rows reference this Project.

        Returns:
            None
        """
        from python_accounting.models import (  # pylint: disable=import-outside-toplevel
            Ledger,
        )

        if (
            session.query(func.count(Ledger.id))  # pylint: disable=not-callable
            .filter(Ledger.entity_id == self.entity_id)
            .filter(Ledger.project_id == self.id)
            .scalar()
            > 0
        ):
            raise HangingTransactionsError("Project")
