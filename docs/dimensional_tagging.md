# Dimensional Tagging: Teams and Projects

## Overview

Teams and Projects are **optional cross-cutting dimensions** that can be attached to line items (and propagated to ledger entries) for analytical reporting. They are orthogonal to accounts and funds — meaning you can slice your financial data by team, by project, or by any combination of fund + team + project without changing your chart of accounts.

### Why Dimensional Tags?

Consider a software company with three engineering teams and two active projects. The company wants to know:

- How much did Team Alpha spend last quarter? (team dimension)
- What is the total cost of Project Phoenix? (project dimension)
- How much did Team Alpha spend on Project Phoenix? (combined dimensions)

Without dimensional tags, you would need to create separate accounts for every combination (e.g., "Engineering Salaries — Team Alpha — Project Phoenix"). This leads to chart-of-accounts explosion. With dimensional tags, you keep a clean chart of accounts and add the team/project context as metadata on each line item.

### Relationship to Funds and Accounts

| Concept | Purpose | Scope | Required? |
|---------|---------|-------|-----------|
| **Account** | Classifies the nature of a transaction (revenue, expense, asset, etc.) | Every transaction | Always |
| **Fund** | Segregates money by restriction or purpose | Line items (when fund accounting enabled) | Only with fund accounting |
| **Team** | Tags transactions by organizational unit | Line items (always optional) | Never |
| **Project** | Tags transactions by project or initiative | Line items (always optional) | Never |

Teams and projects are always optional — they never gate transaction posting or validation. They exist purely for reporting and analysis.

## Creating Teams

```python
from python_accounting.models.team import Team

engineering = Team(
    name="Engineering",
    description="Software engineering department",
    entity_id=entity.id,
)
session.add(engineering)
session.flush()

marketing = Team(
    name="Marketing",
    description="Marketing and communications",
    entity_id=entity.id,
)
session.add(marketing)
session.flush()
```

### Team Properties

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `name` | str | Yes | The display name (auto-title-cased) |
| `description` | str | No | A narrative description |
| `entity_id` | int | Yes | The entity this team belongs to |

### Validation Rules

- `name` is required — a `ValueError` is raised if missing.
- Names are automatically title-cased on save.
- A team cannot be deleted if any `Ledger` rows reference it (`HangingTransactionsError`).

## Creating Projects

```python
from python_accounting.models.project import Project

phoenix = Project(
    name="Project Phoenix",
    description="Next-generation platform rewrite",
    entity_id=entity.id,
)
session.add(phoenix)
session.flush()

atlas = Project(
    name="Project Atlas",
    description="Data infrastructure overhaul",
    entity_id=entity.id,
)
session.add(atlas)
session.flush()
```

### Project Properties

| Property | Type | Required | Description |
|----------|------|----------|-------------|
| `name` | str | Yes | The display name (auto-title-cased) |
| `description` | str | No | A narrative description |
| `entity_id` | int | Yes | The entity this project belongs to |

### Validation Rules

- `name` is required — a `ValueError` is raised if missing.
- Names are automatically title-cased on save.
- A project cannot be deleted if any `Ledger` rows reference it (`HangingTransactionsError`).

## Tagging Line Items

Attach `team_id` and/or `project_id` to line items. These tags propagate to the resulting ledger entries when the transaction is posted.

```python
from python_accounting.models import LineItem

line_item = LineItem(
    narration="Developer salary - January",
    account_id=salary_expense.id,
    amount=8000,
    team_id=engineering.id,
    project_id=phoenix.id,
    entity_id=entity.id,
)
session.add(line_item)
session.flush()

transaction.line_items.add(line_item)
session.add(transaction)
session.flush()

transaction.post(session)
# Ledger entries carry team_id=engineering.id, project_id=phoenix.id
```

You can tag with just a team, just a project, both, or neither:

```python
# Team only
LineItem(narration="...", account_id=..., amount=100, team_id=engineering.id, entity_id=entity.id)

# Project only
LineItem(narration="...", account_id=..., amount=100, project_id=phoenix.id, entity_id=entity.id)

# Both
LineItem(narration="...", account_id=..., amount=100, team_id=engineering.id, project_id=phoenix.id, entity_id=entity.id)

# Neither (standard behavior)
LineItem(narration="...", account_id=..., amount=100, entity_id=entity.id)
```

## Filtering Reports by Team or Project

Financial reports accept optional `team_id` and `project_id` parameters to filter results:

### Filter by Team

```python
from python_accounting.reports import IncomeStatement

# Income statement for Engineering team
engineering_pnl = IncomeStatement(
    session,
    start_date=period_start,
    end_date=period_end,
    team_id=engineering.id,
)
```

### Filter by Project

```python
from python_accounting.reports import IncomeStatement

# Income statement for Project Phoenix
phoenix_pnl = IncomeStatement(
    session,
    start_date=period_start,
    end_date=period_end,
    project_id=phoenix.id,
)
```

### Combined Filtering

All dimensions can be combined. For example, to see the expenses of the Engineering team on Project Phoenix within the Building Fund:

```python
from python_accounting.reports import IncomeStatement

# Fund + Team + Project
filtered = IncomeStatement(
    session,
    start_date=period_start,
    end_date=period_end,
    fund_id=building_fund.id,
    team_id=engineering.id,
    project_id=phoenix.id,
)
```

The same filtering works for all report types:

```python
from python_accounting.reports import BalanceSheet, CashflowStatement, TrialBalance

# Balance Sheet filtered by team
bs = BalanceSheet(session, end_date=period_end, team_id=engineering.id)

# Cash Flow Statement filtered by project
cf = CashflowStatement(session, start_date=period_start, end_date=period_end, project_id=phoenix.id)

# Trial Balance filtered by both
tb = TrialBalance(session, end_date=period_end, team_id=engineering.id, project_id=phoenix.id)
```

### Unfiltered (Consolidated) Reports

Omitting the dimension parameters produces reports that aggregate across all teams and projects:

```python
# Consolidated — includes all teams, all projects, all funds
consolidated = IncomeStatement(session, start_date=period_start, end_date=period_end)
```

## Data Model Summary

```
Entity
  ├── Fund        (fund accounting only)
  ├── Team        (optional dimension)
  ├── Project     (optional dimension)
  └── Transaction
        └── LineItem
              ├── fund_id     → Fund     (required when fund accounting enabled)
              ├── team_id     → Team     (always optional)
              └── project_id  → Project  (always optional)
                    ↓
              Ledger (inherits fund_id, team_id, project_id from LineItem on posting)
```

## Key Design Decisions

1. **Optional by default**: Teams and projects never block transactions. They are purely analytical.

2. **Ledger propagation**: Tags flow from `LineItem` to `Ledger` during posting, ensuring that all downstream queries and reports can filter by these dimensions.

3. **Deletion protection**: Teams and projects cannot be deleted while ledger entries reference them, preserving referential integrity.

4. **Entity isolation**: Like all models, teams and projects are scoped to a single entity via `IsolatingMixin`.

5. **Orthogonal to funds**: You can use teams and projects with or without fund accounting. They are independent dimensions.
