# models/team.py
# Copyright (C) 2024 - 2028 the PythonAccounting authors and contributors
# <see AUTHORS file>
#
# This module is part of PythonAccounting and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

"""
Represents a Team for dimensional tagging of ledger entries.

"""
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, ForeignKey, func
from python_accounting.mixins import IsolatingMixin
from python_accounting.models import Recyclable
from python_accounting.exceptions import HangingTransactionsError


class Team(IsolatingMixin, Recyclable):
    """Represents a Team for cost/revenue tracking."""

    __mapper_args__ = {"polymorphic_identity": "Team"}

    id: Mapped[int] = mapped_column(ForeignKey("recyclable.id"), primary_key=True)
    """(int): The primary key of the Team database record."""
    name: Mapped[str] = mapped_column(String(255))
    """(str): The name of the Team."""
    description: Mapped[str] = mapped_column(String(1000), nullable=True)
    """(`str`, optional): A description of the Team."""

    def __repr__(self) -> str:
        return self.name

    def validate(self, _) -> None:
        """
        Validates the Team properties.

        Raises:
            ValueError: If the Team name is not provided.

        Returns:
            None
        """
        if not self.name:
            raise ValueError("Team name is required.")
        self.name = self.name.title()

    def validate_delete(self, session) -> None:
        """
        Validates if the Team can be deleted.

        Raises:
            HangingTransactionsError: If any Ledger rows reference this Team.

        Returns:
            None
        """
        from python_accounting.models import (  # pylint: disable=import-outside-toplevel
            Ledger,
        )

        if (
            session.query(func.count(Ledger.id))  # pylint: disable=not-callable
            .filter(Ledger.entity_id == self.entity_id)
            .filter(Ledger.team_id == self.id)
            .scalar()
            > 0
        ):
            raise HangingTransactionsError("Team")
