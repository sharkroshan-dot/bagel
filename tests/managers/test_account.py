import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from bagels.models.database.db import Base
from bagels.managers import accounts

@pytest.fixture(scope="function")
def test_db():
    # Create in-memory SQLite database
    engine = create_engine("sqlite:///:memory:")
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    # Create a new session factory bound to the engine
    accounts.Session = sessionmaker(bind=engine)
    
    yield engine
    
    # Clean up
    Base.metadata.drop_all(engine)

def test_create_account(test_db):
    # Test data
    account_data = {
        "name": "Test Account",
        "description": "Test Description",
        "beginningBalance": 1000.0,
        "repaymentDate": 15,
        "hidden": False
    }
    
    # Create account
    new_account = accounts.create_account(account_data)
    
    # Assertions
    assert new_account is not None
    assert new_account.name == "Test Account"
    assert new_account.description == "Test Description"
    assert new_account.beginningBalance == 1000.0
    assert new_account.repaymentDate == 15
    assert new_account.hidden is False
    assert new_account.id is not None
    assert new_account.createdAt is not None
    assert new_account.updatedAt is not None
    assert new_account.deletedAt is None

def test_get_all_accounts(test_db):
    # Create test data
    account_data1 = {
        "name": "Account 1",
        "beginningBalance": 1000.0,
        "hidden": False
    }
    account_data2 = {
        "name": "Account 2",
        "beginningBalance": 2000.0,
        "hidden": True
    }
    
    accounts.create_account(account_data1)
    accounts.create_account(account_data2)
    
    # Get all non-hidden accounts
    visible_accounts = accounts.get_all_accounts(get_hidden=False)
    assert len(visible_accounts) == 1
    assert visible_accounts[0].name == "Account 1"
    
    # Get all accounts including hidden
    all_accounts = accounts.get_all_accounts(get_hidden=True)
    assert len(all_accounts) == 2
    assert {a.name for a in all_accounts} == {"Account 1", "Account 2"}

def test_get_accounts_count(test_db):
    # Create test data
    account_data1 = {
        "name": "Account 1",
        "beginningBalance": 1000.0,
        "hidden": False
    }
    account_data2 = {
        "name": "Account 2",
        "beginningBalance": 2000.0,
        "hidden": True
    }
    
    accounts.create_account(account_data1)
    accounts.create_account(account_data2)
    
    # Test counts
    assert accounts.get_accounts_count(get_hidden=False) == 1
    assert accounts.get_accounts_count(get_hidden=True) == 2

def test_get_account_by_id(test_db):
    # Create test data
    account_data = {
        "name": "Test Account",
        "beginningBalance": 1000.0,
        "hidden": False
    }
    new_account = accounts.create_account(account_data)
    
    # Get account by ID
    retrieved_account = accounts.get_account_by_id(new_account.id)
    
    # Assertions
    assert retrieved_account is not None
    assert retrieved_account.id == new_account.id
    assert retrieved_account.name == "Test Account"
    assert retrieved_account.beginningBalance == 1000.0

def test_get_nonexistent_account(test_db):
    # Try to get an account with non-existent ID
    retrieved_account = accounts.get_account_by_id(999)
    
    # Assertions
    assert retrieved_account is None

def test_update_account(test_db):
    # Create test data
    account_data = {
        "name": "Test Account",
        "beginningBalance": 1000.0,
        "hidden": False
    }
    new_account = accounts.create_account(account_data)
    
    # Update data
    update_data = {
        "name": "Updated Account",
        "description": "New Description",
        "hidden": True
    }
    updated_account = accounts.update_account(new_account.id, update_data)
    
    # Assertions
    assert updated_account is not None
    assert updated_account.name == "Updated Account"
    assert updated_account.description == "New Description"
    assert updated_account.hidden is True
    assert updated_account.beginningBalance == 1000.0  # Unchanged
    assert updated_account.id == new_account.id

def test_update_nonexistent_account(test_db):
    # Try to update non-existent account
    update_data = {"name": "Updated Account"}
    updated_account = accounts.update_account(999, update_data)
    
    # Assertions
    assert updated_account is None

def test_delete_account(test_db):
    # Create test data
    account_data = {
        "name": "Test Account",
        "beginningBalance": 1000.0,
        "hidden": False
    }
    new_account = accounts.create_account(account_data)
    
    # Delete account
    result = accounts.delete_account(new_account.id)
    
    # Assertions
    assert result is True
    
    # Check that the account is marked as deleted
    deleted_account = accounts.get_account_by_id(new_account.id)
    assert deleted_account is not None
    assert deleted_account.deletedAt is not None
    
    # Check that it's not returned in get_all_accounts
    all_accounts = accounts.get_all_accounts(get_hidden=True)
    assert len(all_accounts) == 0

def test_delete_nonexistent_account(test_db):
    # Try to delete non-existent account
    result = accounts.delete_account(999)
    
    # Assertions
    assert result is False
