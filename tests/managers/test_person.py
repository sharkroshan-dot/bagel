import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from bagels.models.database.db import Base
from bagels.managers import persons

@pytest.fixture(scope="function")
def test_db():
    # Create in-memory SQLite database
    engine = create_engine("sqlite:///:memory:")
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    # Create a new session factory bound to the engine
    persons.Session = sessionmaker(bind=engine)
    
    yield engine
    
    # Clean up
    Base.metadata.drop_all(engine)

def test_create_person(test_db):
    # Test data
    person_data = {"name": "John Doe"}
    
    # Create person
    new_person = persons.create_person(person_data)
    
    # Assertions
    assert new_person is not None
    assert new_person.name == "John Doe"
    assert new_person.id is not None
    assert new_person.createdAt is not None
    assert new_person.updatedAt is not None

def test_get_all_persons(test_db):
    # Create test data
    person_data1 = {"name": "John Doe"}
    person_data2 = {"name": "Jane Smith"}
    
    persons.create_person(person_data1)
    persons.create_person(person_data2)
    
    # Get all persons
    all_persons = persons.get_all_persons()
    
    # Assertions
    assert len(all_persons) == 2
    assert any(p.name == "John Doe" for p in all_persons)
    assert any(p.name == "Jane Smith" for p in all_persons)

def test_get_person_by_id(test_db):
    # Create test data
    person_data = {"name": "John Doe"}
    new_person = persons.create_person(person_data)
    
    # Get person by ID
    retrieved_person = persons.get_person_by_id(new_person.id)
    
    # Assertions
    assert retrieved_person is not None
    assert retrieved_person.id == new_person.id
    assert retrieved_person.name == "John Doe"

def test_get_nonexistent_person(test_db):
    # Try to get a person with non-existent ID
    retrieved_person = persons.get_person_by_id(999)
    
    # Assertions
    assert retrieved_person is None

def test_update_person(test_db):
    # Create test data
    person_data = {"name": "John Doe"}
    new_person = persons.create_person(person_data)
    
    # Update data
    update_data = {"name": "John Smith"}
    updated_person = persons.update_person(new_person.id, update_data)
    
    # Assertions
    assert updated_person is not None
    assert updated_person.name == "John Smith"
    assert updated_person.id == new_person.id

def test_update_nonexistent_person(test_db):
    # Try to update non-existent person
    update_data = {"name": "John Smith"}
    updated_person = persons.update_person(999, update_data)
    
    # Assertions
    assert updated_person is None

def test_delete_person(test_db):
    # Create test data
    person_data = {"name": "John Doe"}
    new_person = persons.create_person(person_data)
    
    # Delete person
    result = persons.delete_person(new_person.id)
    
    # Assertions
    assert result is True
    assert persons.get_person_by_id(new_person.id) is None

def test_delete_nonexistent_person(test_db):
    # Try to delete non-existent person
    result = persons.delete_person(999)
    
    # Assertions
    assert result is False
