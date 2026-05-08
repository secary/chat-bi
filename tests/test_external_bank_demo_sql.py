from pathlib import Path


SQL_FILES = (
    Path("data/external_bank_bootstrap.sql"),
    Path("data/external_bank_demo.sql"),
    Path("data/external_bank_business.sql"),
    Path("data/external_bank_semantic.sql"),
)
SQL = "\n".join(path.read_text(encoding="utf-8") for path in SQL_FILES)


def test_external_bank_demo_creates_independent_database():
    assert "CREATE DATABASE IF NOT EXISTS chatbi_bank_external" in SQL
    assert "USE chatbi_bank_external" in SQL


def test_external_bank_demo_covers_banking_relationship_tables():
    for name in (
        "bank_branch",
        "bank_customer",
        "customer_account",
        "deposit_daily_balance",
        "loan_contract",
        "loan_repayment",
        "card_account",
        "channel_transaction",
        "wealth_position",
        "risk_event",
    ):
        assert f"CREATE TABLE {name}" in SQL


def test_external_bank_demo_keeps_chatbi_compatibility_surface():
    assert "CREATE VIEW sales_order AS" in SQL
    assert "CREATE VIEW customer_profile AS" in SQL
    for name in (
        "data_source_config",
        "field_dictionary",
        "metric_definition",
        "dimension_definition",
        "business_term",
        "alias_mapping",
    ):
        assert f"CREATE TABLE {name}" in SQL


def test_external_bank_demo_adds_banking_semantic_aliases():
    for term in ("存款余额", "贷款余额", "AUM", "网点", "支行", "业务类型"):
        assert term in SQL
