import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from bagels.managers import records
from datetime import datetime

from bagels.models.account import Account
from bagels.models.category import Category, Nature
from bagels.models.database.db import Base


@pytest.fixture(scope="function")
def engine():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture(scope="function")
def session(engine):
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


@pytest.fixture(autouse=True)
def setup_test_engine(monkeypatch, engine):
    import bagels.managers.records as record_managers
    from bagels.config import load_config

    load_config()
    record_managers.Session = sessionmaker(bind=engine)
    yield


@pytest.fixture
def account(session):
    account = Account(name="Test Account", beginningBalance=1000.0)
    session.add(account)
    session.commit()
    return account


@pytest.fixture
def category(session):
    category = Category(name="Test Category", nature=Nature.WANT, color="#000000")
    session.add(category)
    session.commit()
    return category


def test_soft_delete_and_restore_record(account, category):
    record = records.create_record(
        {
            "label": "Dinner",
            "amount": 25.0,
            "date": datetime(2026, 5, 1),
            "isIncome": False,
            "isTransfer": False,
            "accountId": account.id,
            "categoryId": category.id,
            "transferToAccountId": None,
        }
    )
    assert record is not None
    records.delete_record(record.id)
    deleted = records.get_deleted_records()
    assert len(deleted) == 1
    assert deleted[0].id == record.id

    restored = records.restore_record(record.id)
    assert restored is not None
    assert restored.deletedAt is None
    remaining = records.get_records(offset_type="all")
    assert any(r.id == record.id for r in remaining)


def test_export_records_to_csv(account, category):
    records.create_record(
        {
            "label": "Groceries",
            "amount": 58.25,
            "date": datetime(2026, 5, 2),
            "isIncome": False,
            "isTransfer": False,
            "accountId": account.id,
            "categoryId": category.id,
            "transferToAccountId": None,
        }
    )

    csv_data = records.export_records_to_csv(offset_type="all")
    assert "Groceries" in csv_data
    assert "58.25" in csv_data
    assert "category" in csv_data.lower() or "account" in csv_data.lower()


def test_import_records_from_csv_parses_common_fields():
    csv_text = "date,label,amount,account,category,isIncome\n2026-05-05,Subscription,12.00,Bank,Utilities,0\n"
    parsed = records.import_records_from_csv(csv_text)
    assert parsed[0]["label"] == "Subscription"
    assert parsed[0]["amount"] == "12.00"
    assert parsed[0]["account"] == "Bank"
    assert parsed[0]["isIncome"] == "0"
