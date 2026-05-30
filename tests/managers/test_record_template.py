import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from bagels.managers import record_templates
from bagels.models.account import Account
from bagels.models.category import Category, Nature
from bagels.models.database.db import Base


# Setup test database
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
    # Replace the global engine with our test engine
    import bagels.managers.record_templates as rt

    rt.Session = sessionmaker(bind=engine)
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


@pytest.fixture
def template_data(account, category):
    return {
        "label": "Test Template",
        "amount": 100.0,
        "accountId": account.id,
        "categoryId": category.id,
        "isIncome": False,
        "isTransfer": False,
        "transferToAccountId": None,
    }


def test_create_template(template_data):
    template = record_templates.create_template(template_data)
    assert template.label == template_data["label"]
    assert template.amount == template_data["amount"]
    assert template.accountId == template_data["accountId"]
    assert template.categoryId == template_data["categoryId"]
    assert template.order == 1  # First template should have order 1


def test_create_multiple_templates(template_data):
    template1 = record_templates.create_template(template_data)
    template2 = record_templates.create_template(template_data)
    assert template1.order == 1
    assert template2.order == 2


def test_get_all_templates(template_data):
    template1 = record_templates.create_template(template_data)
    template2 = record_templates.create_template(template_data)
    templates = record_templates.get_all_templates()
    assert len(templates) == 2
    assert templates[0].id == template1.id
    assert templates[1].id == template2.id
    assert templates[0].order < templates[1].order


def test_get_template_by_id(template_data):
    template = record_templates.create_template(template_data)
    retrieved = record_templates.get_template_by_id(template.id)
    assert retrieved is not None
    assert retrieved.id == template.id
    assert retrieved.label == template.label


def test_get_nonexistent_template():
    template = record_templates.get_template_by_id(999)
    assert template is None


def test_get_adjacent_template(template_data):
    template1 = record_templates.create_template(template_data)
    template2 = record_templates.create_template(template_data)
    template3 = record_templates.create_template(template_data)

    # Test getting next template
    next_id = record_templates.get_adjacent_template(template1.id, "next")
    assert next_id == template2.id

    # Test getting previous template
    prev_id = record_templates.get_adjacent_template(template2.id, "previous")
    assert prev_id == template1.id

    # Test getting next template for last template
    next_id = record_templates.get_adjacent_template(template3.id, "next")
    assert next_id == -1

    # Test getting previous template for first template
    prev_id = record_templates.get_adjacent_template(template1.id, "previous")
    assert prev_id == -1


def test_update_template(template_data):
    template = record_templates.create_template(template_data)
    updates = {"label": "Updated Template", "amount": 200.0}
    updated = record_templates.update_template(template.id, updates)
    assert updated.label == updates["label"]
    assert updated.amount == updates["amount"]
    assert updated.accountId == template.accountId  # Unchanged fields remain the same


def test_update_nonexistent_template(template_data):
    updated = record_templates.update_template(999, {"label": "New Label"})
    assert updated is None


def test_swap_template_order(template_data):
    template1 = record_templates.create_template(template_data)
    template2 = record_templates.create_template(template_data)
    template3 = record_templates.create_template(template_data)

    # Test swapping with next template
    swapped = record_templates.swap_template_order(template1.id, "next")
    templates = record_templates.get_all_templates()
    assert templates[0].id == template2.id
    assert templates[1].id == template1.id

    # Test swapping with previous template
    swapped = record_templates.swap_template_order(template1.id, "previous")
    templates = record_templates.get_all_templates()
    assert templates[0].id == template1.id
    assert templates[1].id == template2.id


def test_swap_template_order_edge_cases(template_data):
    template1 = record_templates.create_template(template_data)
    template2 = record_templates.create_template(template_data)

    # Test swapping first template with previous (should fail gracefully)
    swapped = record_templates.swap_template_order(template1.id, "previous")
    templates = record_templates.get_all_templates()
    assert templates[0].id == template1.id

    # Test swapping last template with next (should fail gracefully)
    swapped = record_templates.swap_template_order(template2.id, "next")
    templates = record_templates.get_all_templates()
    assert templates[1].id == template2.id


def test_delete_template(template_data):
    template1 = record_templates.create_template(template_data)
    template2 = record_templates.create_template(template_data)
    template3 = record_templates.create_template(template_data)

    # Delete middle template
    success = record_templates.delete_template(template2.id)
    assert success is True

    # Check remaining templates
    templates = record_templates.get_all_templates()
    assert len(templates) == 2
    assert templates[0].id == template1.id
    assert templates[1].id == template3.id
    assert templates[0].order == 1  # Orders should be resequenced
    assert templates[1].order == 2


def test_delete_nonexistent_template():
    success = record_templates.delete_template(999)
    assert success is False


def test_template_validation(template_data, account):
    # Test negative amount
    invalid_data = template_data.copy()
    invalid_data["amount"] = -100.0
    with pytest.raises(
        Exception
    ):  # SQLAlchemy will raise an exception due to CheckConstraint
        record_templates.create_template(invalid_data)

    # Test transfer template
    transfer_data = template_data.copy()
    transfer_data["isTransfer"] = True
    transfer_data["transferToAccountId"] = account.id
    template = record_templates.create_template(transfer_data)
    assert template.isTransfer is True
    assert template.transferToAccountId == account.id

    # Test invalid transfer (transfer with income)
    invalid_transfer = template_data.copy()
    invalid_transfer["isTransfer"] = True
    invalid_transfer["isIncome"] = True
    invalid_transfer["transferToAccountId"] = account.id
    with pytest.raises(
        Exception
    ):  # SQLAlchemy will raise an exception due to CheckConstraint
        record_templates.create_template(invalid_transfer)
