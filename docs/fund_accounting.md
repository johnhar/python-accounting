# Fund Accounting

## What Is Fund Accounting?

Fund accounting is a system of accounting used by non-profit organizations, governments, and other entities that need to track money by *purpose* rather than by *profit*. Instead of a single pool of money, the organization maintains separate **funds**, each representing resources that are restricted or designated for a specific purpose.

For example, a charity might have:

- A **General Fund** for day-to-day operations
- A **Building Fund** for a capital campaign
- A **Scholarship Fund** restricted by donors for student grants
- A **Endowment Fund** whose principal cannot be spent

Every dollar that enters or leaves the organization is tagged with the fund it belongs to. This ensures that restricted resources are never accidentally spent on unauthorized purposes, and that the organization can demonstrate compliance with donor restrictions and grant requirements.

## How Fund Accounting Differs from Regular Accounting

In standard commercial accounting, the entity has one unified set of books. Revenue minus expenses equals profit, and the owners decide how to allocate that profit.

In fund accounting:

| Aspect | Commercial Accounting | Fund Accounting |
|--------|----------------------|-----------------|
| Goal | Measure profit | Demonstrate stewardship |
| Money tracking | Single pool | Segregated by fund |
| Revenue | Increases profit | Increases a specific fund balance |
| Expenses | Reduce profit | Reduce a specific fund balance |
| Bottom line | Net income | Change in net assets by fund |
| Reports | Consolidated only | Per-fund and consolidated |

The double-entry mechanics remain the same — every transaction still produces balanced debit/credit pairs. The difference is that every ledger entry carries a `fund_id` tag, allowing the system to produce fund-specific financial statements.

## Enabling Fund Accounting

Fund accounting is controlled by a flag on the `Entity` model. This flag is set at creation time and **cannot be changed afterward** — it is immutable. This prevents accidental mode switches that would leave existing transactions in an inconsistent state.

```python
from python_accounting.models import Entity

# Enable fund accounting at entity creation
entity = Entity(
    name="Hope Foundation",
    fund_accounting=True,
    currency_id=currency.id,
)
session.add(entity)
session.flush()
```

Attempting to change `fund_accounting` after creation raises an `ImmutableFieldError`:

```python
entity.fund_accounting = False
session.commit()  # Raises ImmutableFieldError
```

If fund accounting is **not** enabled (the default), all fund-related columns are ignored and the system behaves as standard commercial accounting.

## Creating Funds

Once fund accounting is enabled, create `Fund` objects to represent each segregated pool of resources:

```python
from python_accounting.models.fund import Fund

general = Fund(
    name="General Fund",
    description="Unrestricted operating resources",
    fund_code="GEN",
    entity_id=entity.id,
)
session.add(general)
session.flush()

building = Fund(
    name="Building Fund",
    description="Capital campaign for new facility",
    fund_code="BLD",
    entity_id=entity.id,
)
session.add(building)
session.flush()
```

### Fund Properties

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `name` | str | Yes | The display name of the fund (auto-title-cased) |
| `description` | str | No | A narrative description of the fund's purpose |
| `fund_code` | str | No | A short identifying code (e.g., "GEN", "BLD") |
| `entity_id` | int | Yes | The entity this fund belongs to (via `IsolatingMixin`) |

### Validation Rules

- `name` is required — a `ValueError` is raised if it is missing.
- Names are automatically title-cased on save.
- A fund cannot be deleted if any `Ledger` rows reference it (`HangingTransactionsError`).

## Using Funds on Line Items

When fund accounting is enabled, every `LineItem` must carry a `fund_id`. This tag propagates to the resulting `Ledger` entries when the transaction is posted.

```python
from python_accounting.models import LineItem

line_item = LineItem(
    narration="Donation received",
    account_id=revenue_account.id,
    amount=5000,
    fund_id=general.id,
    entity_id=entity.id,
)
session.add(line_item)
session.flush()

transaction.line_items.add(line_item)
session.add(transaction)
session.flush()

transaction.post(session)
# Ledger entries are created with fund_id=general.id
```

If fund accounting is enabled and a line item is missing its `fund_id`, a `MissingFundError` is raised during validation.

## Inter-Fund Transfers

Sometimes resources need to move between funds — for example, transferring unrestricted money from the General Fund to the Building Fund. This is accomplished with a `FundTransfer`.

### Logical vs. Physical Transfers

There are two types of inter-fund transfers:

- **Logical transfer**: The money stays in the same bank account, but the fund tag changes. This is the most common case. The journal entry debits and credits the same account, differing only in the fund tag on each side.

- **Physical transfer**: The money moves between different bank accounts (e.g., from an operating account to a capital campaign account). This involves different accounts on each side of the entry.

### Creating a Fund Transfer

```python
from python_accounting.transactions.fund_transfer import FundTransfer

# Logical transfer: same bank account, different funds
transfer = FundTransfer(
    narration="Transfer to building campaign",
    transaction_date=datetime.now(),
    account_id=bank_account.id,        # source account
    source_fund_id=general.id,
    destination_fund_id=building.id,
    entity_id=entity.id,
)
session.add(transfer)
session.flush()

line_item = LineItem(
    narration="Building fund allocation",
    account_id=bank_account.id,         # destination account (same for logical)
    amount=10000,
    fund_id=building.id,                # destination fund
    entity_id=entity.id,
)
session.add(line_item)
session.flush()

transfer.line_items.add(line_item)
session.add(transfer)
session.flush()

transfer.post(session)
```

### Validation Rules for Fund Transfers

- Fund accounting must be enabled on the entity (`FundAccountingDisabledError`)
- Source and destination funds must be different (`SameFundTransferError`)
- Both source and destination funds must exist and belong to the same entity

## Fund-Filtered Reports

When fund accounting is enabled, all financial reports can be filtered by fund. This produces a statement showing only the transactions tagged with that fund.

### Per-Fund Reports

```python
from python_accounting.reports import IncomeStatement, BalanceSheet

# Income statement for the General Fund only
income_stmt = IncomeStatement(
    session,
    start_date=period_start,
    end_date=period_end,
    fund_id=general.id,
)

# Balance sheet for the Building Fund only
balance = BalanceSheet(
    session,
    end_date=period_end,
    fund_id=building.id,
)
```

### Consolidated Reports

Omitting the `fund_id` parameter produces a consolidated report across all funds — the traditional view:

```python
# Consolidated income statement (all funds)
consolidated = IncomeStatement(session, start_date=period_start, end_date=period_end)
```

## Requirements Specification

The following are the canonical behavioral rules for fund accounting in this system:

1. **Entity-level flag**: The `fund_accounting` boolean on `Entity` determines whether fund accounting is active. It defaults to `False`.

2. **Immutability**: Once set at creation, `fund_accounting` cannot be changed. Attempts to modify it raise `ImmutableFieldError`.

3. **Fund requirement**: When fund accounting is enabled, every `LineItem` must have a non-null `fund_id`. Missing fund tags raise `MissingFundError`.

4. **Ledger propagation**: When a transaction is posted, the `fund_id` from each `LineItem` is copied to the resulting `Ledger` entries.

5. **Fund isolation in reports**: Reports accept an optional `fund_id` parameter. When provided, only ledger entries matching that fund are included in balances and totals.

6. **Consolidated default**: When no `fund_id` is specified, reports aggregate across all funds (standard behavior).

7. **Fund transfers**: The `FundTransfer` transaction type moves resources between funds. It requires:
   - Fund accounting to be enabled (`FundAccountingDisabledError`)
   - Different source and destination funds (`SameFundTransferError`)

8. **Deletion protection**: A `Fund` cannot be deleted if any `Ledger` rows reference it (`HangingTransactionsError`).

9. **Entity isolation**: Funds are scoped to an entity via `IsolatingMixin`, like all other models.

10. **No retroactive changes**: Because `fund_accounting` is immutable, there is no migration path from commercial to fund accounting or vice versa. This is by design — mixing tagged and untagged transactions would compromise reporting integrity.
