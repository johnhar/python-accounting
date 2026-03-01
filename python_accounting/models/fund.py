# models/fund.py
# Copyright (C) 2024 - 2028 the PythonAccounting authors and contributors
# <see AUTHORS file>
#
# This module is part of PythonAccounting and is released under
# the MIT License: https://www.opensource.org/licenses/mit-license.php

"""
Represents a Fund for fund accounting.

"""
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, ForeignKey, func
from python_accounting.mixins import IsolatingMixin
from python_accounting.models import Recyclable
from python_accounting.exceptions import HangingTransactionsError


class Fund(IsolatingMixin, Recyclable):
    """Represents a Fund for tracking money by purpose in fund accounting."""

    __mapper_args__ = {"polymorphic_identity": "Fund"}

    id: Mapped[int] = mapped_column(ForeignKey("recyclable.id"), primary_key=True)
    """(int): The primary key of the Fund database record."""
    name: Mapped[str] = mapped_column(String(255))
    """(str): The name of the Fund."""
    description: Mapped[str] = mapped_column(String(1000), nullable=True)
    """(`str`, optional): A description of the Fund's purpose."""
    fund_code: Mapped[str] = mapped_column(String(255), nullable=True)
    """(`str`, optional): An identifying code for the Fund."""

    def __repr__(self) -> str:
        return self.name

    def validate(self, _) -> None:
        """
        Validates the Fund properties.

        Raises:
            ValueError: If the Fund name is not provided.

        Returns:
            None
        """
        if not self.name:
            raise ValueError("Fund name is required.")
        self.name = self.name.title()

    def validate_delete(self, session) -> None:
        """
        Validates if the Fund can be deleted.

        Raises:
            HangingTransactionsError: If any Ledger rows reference this Fund.

        Returns:
            None
        """
        from python_accounting.models import (  # pylint: disable=import-outside-toplevel
            Ledger,
        )

        if (
            session.query(func.count(Ledger.id))  # pylint: disable=not-callable
            .filter(Ledger.entity_id == self.entity_id)
            .filter(Ledger.fund_id == self.id)
            .scalar()
            > 0
        ):
            raise HangingTransactionsError("Fund")
