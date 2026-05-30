import copy
from bagels.managers.accounts import get_all_accounts_with_balance
from bagels.managers.persons import get_person_by_id
from bagels.forms.form import Form, FormField, Option, Options


class PersonForm:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    # ------------ Blueprints ------------ #

    FORM = Form(
        fields=[
            FormField(
                placeholder="Steve",
                title="Name",
                key="name",
                type="string",
                is_required=True,
            ),
            FormField(
                title="Account",
                key="accountId",
                type="autocomplete",
                options=Options(),
                is_required=True,
                placeholder="Select Account",
            ),
        ]
    )

    def __init__(self):
        self._populate_account_options()

    def _populate_account_options(self) -> None:
        accounts = get_all_accounts_with_balance()
        self.FORM.fields[1].options = Options(
            items=[
                Option(text=account.name, value=account.id)
                for account in accounts
            ]
        )
        if accounts:
            self.FORM.fields[1].default_value = accounts[0].id
            self.FORM.fields[1].default_value_text = accounts[0].name
    # ------------- Builders ------------- #

    def get_filled_form(self, personId: int):
        form = copy.deepcopy(self.FORM)
        person = get_person_by_id(personId)
        if person is None:
            return form

        for field in form.fields:
            if field.key == "accountId":
                if person.account:
                    field.default_value = person.account.id
                    field.default_value_text = person.account.name
                else:
                    field.default_value = None
                    field.default_value_text = None
            else:
                value = getattr(person, field.key)
                field.default_value = str(value) if value is not None else ""
        return form

    def get_form(self):
        return copy.deepcopy(self.FORM)
