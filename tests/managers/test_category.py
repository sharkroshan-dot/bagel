import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from bagels.models.database.db import Base
from bagels.models.category import Nature
from bagels.managers import categories

@pytest.fixture(scope="function")
def test_db():
    # Create in-memory SQLite database
    engine = create_engine("sqlite:///:memory:")
    
    # Create all tables
    Base.metadata.create_all(engine)
    
    # Create a new session factory bound to the engine
    categories.Session = sessionmaker(bind=engine)
    
    yield engine
    
    # Clean up
    Base.metadata.drop_all(engine)

def test_create_category(test_db):
    # Test data
    category_data = {
        "name": "Test Category",
        "nature": Nature.WANT,
        "color": "#FF0000"
    }
    
    # Create category
    new_category = categories.create_category(category_data)
    
    # Assertions
    assert new_category is not None
    assert new_category.name == "Test Category"
    assert new_category.nature == Nature.WANT
    assert new_category.color == "#FF0000"
    assert new_category.id is not None
    assert new_category.createdAt is not None
    assert new_category.updatedAt is not None
    assert new_category.deletedAt is None
    assert new_category.parentCategoryId is None

def test_create_subcategory(test_db):
    # Create parent category first
    parent_data = {
        "name": "Parent Category",
        "nature": Nature.NEED,
        "color": "#00FF00"
    }
    parent = categories.create_category(parent_data)
    
    # Create subcategory
    child_data = {
        "name": "Child Category",
        "nature": Nature.WANT,
        "color": "#0000FF",
        "parentCategoryId": parent.id
    }
    child = categories.create_category(child_data)
    
    # Assertions
    assert child is not None
    assert child.parentCategoryId == parent.id
    assert child.name == "Child Category"

def test_get_categories_count(test_db):
    # Create test categories
    category_data1 = {
        "name": "Category 1",
        "nature": Nature.WANT,
        "color": "#FF0000"
    }
    category_data2 = {
        "name": "Category 2",
        "nature": Nature.NEED,
        "color": "#00FF00"
    }
    
    categories.create_category(category_data1)
    categories.create_category(category_data2)
    
    # Test count
    assert categories.get_categories_count() == 2

def test_get_all_categories_tree(test_db):
    # Create test categories with hierarchy
    parent_data = {
        "name": "Parent",
        "nature": Nature.NEED,
        "color": "#FF0000"
    }
    parent = categories.create_category(parent_data)
    
    child_data = {
        "name": "Child",
        "nature": Nature.WANT,
        "color": "#00FF00",
        "parentCategoryId": parent.id
    }
    categories.create_category(child_data)
    
    # Get tree
    tree = categories.get_all_categories_tree()
    
    # Assertions
    assert len(tree) == 2  # Parent and child nodes
    assert tree[0][0].name == "Parent"  # First node is parent
    assert tree[1][0].name == "Child"  # Second node is child
    assert tree[1][0].parentCategoryId == parent.id

def test_get_all_categories_by_freq(test_db):
    # Create test categories
    category_data = {
        "name": "Test Category",
        "nature": Nature.WANT,
        "color": "#FF0000"
    }
    categories.create_category(category_data)
    
    # Get categories by frequency
    result = categories.get_all_categories_by_freq()
    
    # Assertions
    assert len(result) == 1
    category, count = result[0]
    assert category.name == "Test Category"
    assert count == 0  # No records yet

def test_get_category_by_id(test_db):
    # Create test category
    category_data = {
        "name": "Test Category",
        "nature": Nature.WANT,
        "color": "#FF0000"
    }
    new_category = categories.create_category(category_data)
    
    # Get category by ID
    retrieved_category = categories.get_category_by_id(new_category.id)
    
    # Assertions
    assert retrieved_category is not None
    assert retrieved_category.id == new_category.id
    assert retrieved_category.name == "Test Category"

def test_get_nonexistent_category(test_db):
    # Try to get a category with non-existent ID
    retrieved_category = categories.get_category_by_id(999)
    
    # Assertions
    assert retrieved_category is None

def test_update_category(test_db):
    # Create test category
    category_data = {
        "name": "Test Category",
        "nature": Nature.WANT,
        "color": "#FF0000"
    }
    new_category = categories.create_category(category_data)
    
    # Update data
    update_data = {
        "name": "Updated Category",
        "nature": Nature.NEED,
        "color": "#00FF00"
    }
    updated_category = categories.update_category(new_category.id, update_data)
    
    # Assertions
    assert updated_category is not None
    assert updated_category.name == "Updated Category"
    assert updated_category.nature == Nature.NEED
    assert updated_category.color == "#00FF00"
    assert updated_category.id == new_category.id

def test_update_nonexistent_category(test_db):
    # Try to update non-existent category
    update_data = {"name": "Updated Category"}
    updated_category = categories.update_category(999, update_data)
    
    # Assertions
    assert updated_category is None

def test_delete_category(test_db):
    # Create test category
    category_data = {
        "name": "Test Category",
        "nature": Nature.WANT,
        "color": "#FF0000"
    }
    new_category = categories.create_category(category_data)
    
    # Delete category
    result = categories.delete_category(new_category.id)
    
    # Assertions
    assert result is True
    
    # Verify the category is marked as deleted
    deleted_category = categories.get_category_by_id(new_category.id)
    assert deleted_category is None  # Should not be returned by get_category_by_id
    
    # Verify it's not returned in counts
    assert categories.get_categories_count() == 0

def test_delete_nonexistent_category(test_db):
    # Try to delete non-existent category
    result = categories.delete_category(999)
    
    # Assertions
    assert result is False
