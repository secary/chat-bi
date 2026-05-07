"""Dashboard overview aggregation (no live MySQL required)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from backend.dashboard_overview import build_dashboard_overview


def test_build_dashboard_overview_shape(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_one(_sql: str, _args=None):
        return {
            "total_sales": Decimal("100.5"),
            "row_count": 2,
            "min_date": date(2026, 1, 5),
            "max_date": date(2026, 4, 1),
            "region_count": 2,
        }

    def fake_all(sql: str, _args=None):
        if "customer_profile" in sql:
            return [{"region": "华东", "active_customers": 12}]
        if "DATE_FORMAT" in sql:
            return [{"month": "2026-01", "sales_amount": Decimal("40")}]
        return [{"region": "华东", "sales_amount": Decimal("60.5")}]

    monkeypatch.setattr("backend.dashboard_overview.business_fetch_one", fake_one)
    monkeypatch.setattr("backend.dashboard_overview.business_fetch_all", fake_all)
    monkeypatch.setattr("backend.dashboard_overview.safe_table_count", lambda _t: 3)

    out = build_dashboard_overview()

    assert out["kpis"]["total_sales"] == 100.5
    assert out["kpis"]["row_count"] == 2
    assert out["kpis"]["min_date"] == "2026-01-05"
    assert out["sales_by_region"][0]["region"] == "华东"
    assert out["sales_by_month"][0]["month"] == "2026-01"
    assert out["customer_by_region"][0]["active_customers"] == 12
    assert out["semantic_counts"]["alias_mapping"] == 3
    assert isinstance(out["warnings"], list)


def test_safe_table_count_invalid_name(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.business_db import safe_table_count

    assert safe_table_count("bad;drop") == 0
