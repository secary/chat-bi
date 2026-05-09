from backend.renderers.kpi import build_kpi_cards


def test_build_kpi_cards_does_not_reuse_first_numeric_for_unknown_fields():
    config = [
        {"label": "销售额", "field": "total_sales", "unit": "元", "default": "--"},
        {"label": "订单数", "field": "order_count", "unit": "笔", "default": "--"},
        {"label": "客户数", "field": "customer_count", "unit": "家", "default": "--"},
    ]
    rows = [{"sales_amount": "1653000.00", "region": "华东"}]

    cards = build_kpi_cards(config, rows)

    assert [card["value"] for card in cards] == ["--", "--", "--"]


def test_build_kpi_cards_uses_exact_field_when_present():
    config = [
        {"label": "销售额", "field": "sales_amount", "unit": "元", "default": "--"},
    ]
    rows = [{"sales_amount": "1653000.00", "region": "华东"}]

    cards = build_kpi_cards(config, rows)

    assert cards[0]["value"] == "1653000.00"
