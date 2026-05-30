import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from bagels.models.database.db import Base
from bagels.models.account import Account
from bagels.models.record import Record
from bagels.models.split import Split
from bagels.models.person import Person
from bagels.models.category import Category, Nature
from bagels.managers import accounts

# Test fixtures
@pytest.fixture(scope="function")
def engine():
    """Create a test-specific database engine."""
    return create_engine("sqlite:///:memory:")

@pytest.fixture(scope="function")
def setup_test_database(engine):
    """Create all tables in the test database."""
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)

@pytest.fixture(scope="function")
def session(engine, setup_test_database):
    """Create a new session for a test."""
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()

@pytest.fixture
def test_data(session):
    """Create test accounts, categories, and people."""
    # Create test accounts
    account1 = Account(name="Account 1", beginningBalance=1000.0)
    account2 = Account(name="Account 2", beginningBalance=500.0)
    session.add_all([account1, account2])
    
    # Create a test category
    category = Category(name="Test Category", nature=Nature.NEED, color="#FF0000")
    session.add(category)
    
    # Create a test person
    person = Person(name="Test Person")
    session.add(person)
    
    session.commit()
    
    return {
        "account1": account1,
        "account2": account2,
        "category": category,
        "person": person
    }

def test_basic_balance_calculation(session, test_data):
    """Test balance calculation with basic income and expense records."""
    # Create test records
    income_record = Record(
        label="Test Income",
        amount=200.0,
        accountId=test_data["account1"].id,
        categoryId=test_data["category"].id,
        isIncome=True,
        date=datetime.now()
    )
    expense_record = Record(
        label="Test Expense",
        amount=150.0,
        accountId=test_data["account1"].id,
        categoryId=test_data["category"].id,
        isIncome=False,
        date=datetime.now()
    )
    session.add_all([income_record, expense_record])
    session.commit()
    
    # Calculate expected balance: 1000 (beginning) + 200 (income) - 150 (expense) = 1050
    balance = accounts.get_account_balance(test_data["account1"].id, session)
    assert balance == 1050.0

def test_transfer_balance_calculation(session, test_data):
    """Test balance calculation with transfers between accounts."""
    # Create a transfer record
    transfer_record = Record(
        label="Test Transfer",
        amount=300.0,
        accountId=test_data["account1"].id,
        isTransfer=True,
        transferToAccountId=test_data["account2"].id,
        date=datetime.now()
    )
    session.add(transfer_record)
    session.commit()
    
    # Calculate expected balances
    # Account 1: 1000 (beginning) - 300 (transfer out) = 700
    balance1 = accounts.get_account_balance(test_data["account1"].id, session)
    assert balance1 == 700.0
    
    # Account 2: 500 (beginning) + 300 (transfer in) = 800
    balance2 = accounts.get_account_balance(test_data["account2"].id, session)
    assert balance2 == 800.0

def test_split_balance_calculation(session, test_data):
    """Test balance calculation with splits."""
    # Create a record with splits
    record = Record(
        label="Test Split Record",
        amount=300.0,
        accountId=test_data["account1"].id,
        categoryId=test_data["category"].id,
        isIncome=False,
        date=datetime.now()
    )
    session.add(record)
    session.flush()
    
    # Create splits
    split1 = Split(
        recordId=record.id,
        amount=100.0,
        personId=test_data["person"].id,
        isPaid=True,
        accountId=test_data["account1"].id,
        paidDate=datetime.now()
    )
    split2 = Split(
        recordId=record.id,
        amount=100.0,
        personId=test_data["person"].id,
        isPaid=False,
        accountId=test_data["account1"].id
    )
    session.add_all([split1, split2])
    session.commit()
    
    # Calculate expected balance
    # 1000 (beginning) - 300 (expense) + 100 (paid split) = 800
    balance = accounts.get_account_balance(test_data["account1"].id, session)
    assert balance == 800.0

def test_combined_balance_calculation(session, test_data):
    """Test balance calculation with a combination of transactions."""
    # Create various transactions
    income_record = Record(
        label="Income",
        amount=500.0,
        accountId=test_data["account1"].id,
        categoryId=test_data["category"].id,
        isIncome=True,
        date=datetime.now()
    )
    expense_record = Record(
        label="Expense",
        amount=200.0,
        accountId=test_data["account1"].id,
        categoryId=test_data["category"].id,
        isIncome=False,
        date=datetime.now()
    )
    transfer_record = Record(
        label="Transfer",
        amount=300.0,
        accountId=test_data["account1"].id,
        isTransfer=True,
        transferToAccountId=test_data["account2"].id,
        date=datetime.now()
    )
    split_record = Record(
        label="Split Record",
        amount=400.0,
        accountId=test_data["account1"].id,
        categoryId=test_data["category"].id,
        isIncome=False,
        date=datetime.now()
    )
    session.add_all([income_record, expense_record, transfer_record, split_record])
    session.flush()
    
    # Create splits
    split = Split(
        recordId=split_record.id,
        amount=200.0,
        personId=test_data["person"].id,
        isPaid=True,
        accountId=test_data["account1"].id,
        paidDate=datetime.now()
    )
    session.add(split)
    session.commit()
    
    # Calculate expected balance for Account 1
    # 1000 (beginning)
    # + 500 (income)
    # - 200 (expense)
    # - 300 (transfer out)
    # - 400 (split record expense)
    # + 200 (paid split)
    # = 800
    balance1 = accounts.get_account_balance(test_data["account1"].id, session)
    assert balance1 == 800.0
    
    # Calculate expected balance for Account 2
    # 500 (beginning) + 300 (transfer in) = 800
    balance2 = accounts.get_account_balance(test_data["account2"].id, session)
    assert balance2 == 800.0
