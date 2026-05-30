import platform
import subprocess
from functools import partial
from typing import TYPE_CHECKING, cast

from textual.command import DiscoveryHit, Hit, Hits, Provider
from textual.types import IgnoreReturnCallbackType

import bagels.config as config
from bagels.config import write_state
from bagels.forms.form import Form, FormField
from bagels.forms.record_forms import RecordForm
from bagels.locations import config_file
from bagels.managers.records import (
    create_record,
    create_record_and_splits,
    export_records_to_csv,
    get_deleted_records,
    import_records_from_csv,
    restore_record,
)
from bagels.managers.samples import create_sample_entries
from bagels.models.database.app import wipe_database
from bagels.components.modules.records import Records
from bagels.modals.record import RecordModal
from bagels.modals.input import InputModal

if TYPE_CHECKING:
    from bagels.app import App


class AppProvider(Provider):
    @property
    def commands(
        self,
    ) -> tuple[tuple[str, IgnoreReturnCallbackType, str, bool], ...]:
        app = self.app

        commands_to_show: list[tuple[str, IgnoreReturnCallbackType, str, bool]] = [
            ("app: quit", app.action_quit, "Quit App", True),
            (
                "config: toggle update check",
                self._action_toggle_update_check,
                "Toggle update check on startup",
                True,
            ),
            (
                "config: toggle footer",
                self._action_toggle_footer,
                "Toggle the footer and hide hotkey hints",
                True,
            ),
            (
                "config: open config file",
                self._action_open_config_file,
                "Open the config file in the default editor",
                True,
            ),
            (
                "dev: create sample entries",
                self._action_create_sample_entries,
                "Create sample entries defined in static/sample_entries.yaml",
                False,
            ),
            (
                "record: quick capture",
                self._action_quick_capture,
                "Capture a new record from the current home filters",
                True,
            ),
            (
                "record: restore last deleted",
                self._action_restore_last_deleted,
                "Restore the most recently deleted record",
                True,
            ),
            (
                "record: export current records",
                self._action_export_records,
                "Export the currently visible records to a CSV file",
                True,
            ),
            (
                "record: import records from csv",
                self._action_import_records,
                "Import records from a CSV file using account and category names",
                False,
            ),
            (
                "dev: wipe database",
                self._action_wipe_database,
                "Delete everything from the database",
                False,
            ),
            *self.get_theme_commands(),
        ]

        return tuple(commands_to_show)

    async def discover(self) -> Hits:
        """Handle a request for the discovery commands for this provider.

        Yields:
            Commands that can be discovered.
        """
        for name, runnable, help_text, show_discovery in self.commands:
            if show_discovery:
                yield DiscoveryHit(
                    name,
                    runnable,
                    help=help_text,
                )

    async def search(self, query: str) -> Hits:
        """Handle a request to search for commands that match the query.

        Args:
            query: The user input to be matched.

        Yields:
            Command hits for use in the command palette.
        """
        matcher = self.matcher(query)
        for name, runnable, help_text, _ in self.commands:
            if (match := matcher.match(name)) > 0:
                yield Hit(
                    match,
                    matcher.highlight(name),
                    runnable,
                    help=help_text,
                )

    def get_theme_commands(
        self,
    ) -> tuple[tuple[str, IgnoreReturnCallbackType, str, bool], ...]:
        app = self.app
        return tuple(self.get_theme_command(theme) for theme in app.themes)

    def get_theme_command(
        self, theme_name: str
    ) -> tuple[str, IgnoreReturnCallbackType, str, bool]:
        return (
            f"theme: {theme_name}",
            partial(self.app.command_theme, theme_name),
            f"Set the theme to {theme_name}",
            True,
        )

    @property
    def app(self) -> "App":
        return cast("App", self.screen.app)

    def _action_create_sample_entries(self) -> None:
        create_sample_entries()
        self.app.refresh(layout=True, recompose=True)

    def _action_wipe_database(self) -> None:
        wipe_database()
        self.app.refresh(layout=True, recompose=True)

        # def check_delete(result) -> None:

        # self.app.push_screen(
        #     ConfirmationModal(
        #         message="Are you sure you want to wipe the database?",
        #     ),
        #     callback=check_delete,
        # )

    def _find_records_module(self):
        try:
            return self.app.query_one(Records)
        except Exception:
            return None

    def _action_quick_capture(self) -> None:
        records_module = self._find_records_module()
        if records_module is None:
            self.app.notify(
                title="Quick capture unavailable",
                message="Switch to the Home page first.",
                severity="warning",
            )
            return

        record_modal = RecordModal(
            "Quick Capture",
            form=RecordForm().get_form(records_module.page_parent.mode),
            splitForm=Form(),
            date=records_module.page_parent.mode["date"],
        )

        def callback(result):
            if not result:
                return
            try:
                create_record_and_splits(result["record"], result["splits"])
            except Exception as exc:
                self.app.notify(title="Error", message=str(exc), severity="error")
                return
            self.app.notify(
                title="Quick Capture",
                message="Record added successfully.",
                severity="success",
                timeout=3,
            )
            records_module.page_parent.rebuild(templates=result.get("createTemplate", False))

        self.app.push_screen(record_modal, callback=callback)

    def _action_restore_last_deleted(self) -> None:
        deleted = get_deleted_records()
        if not deleted:
            self.app.notify(
                title="Nothing to restore",
                message="No deleted records found.",
                severity="information",
                timeout=3,
            )
            return
        restored = restore_record(deleted[0].id)
        if restored:
            self.app.notify(
                title="Restored",
                message=f"Restored {restored.label}.",
                severity="success",
                timeout=3,
            )
            self.app.refresh(layout=True, recompose=True)
        else:
            self.app.notify(
                title="Restore failed",
                message="Could not restore the most recent deleted record.",
                severity="error",
                timeout=3,
            )

    def _action_export_records(self) -> None:
        records_module = self._find_records_module()
        if records_module is None:
            self.app.notify(
                title="Export unavailable",
                message="Switch to the Home page first.",
                severity="warning",
            )
            return

        home_filter = records_module.page_parent.filter
        record_filters = {
            "offset": home_filter["offset"],
            "offset_type": home_filter["offset_type"],
            "account_id": records_module.page_parent.mode["accountId"]["default_value"]
            if home_filter["byAccount"]
            else None,
            "category_piped_names": records_module.FILTERS["category"](),
            "operator_amount": records_module.FILTERS["amount"](),
            "label": records_module.FILTERS["label"](),
        }

        default_path = config_file().parent / "records_export.csv"
        export_form = Form(
            fields=[
                FormField(
                    title="Path",
                    key="path",
                    type="string",
                    default_value=str(default_path),
                    placeholder="Enter destination CSV path",
                )
            ]
        )
        self.app.push_screen(
            InputModal("Export records to CSV", form=export_form),
            callback=lambda result: self._save_export_csv(result, record_filters),
        )

    def _save_export_csv(self, result, record_filters):
        if not result:
            return
        try:
            output = export_records_to_csv(**record_filters)
            path = result["path"]
            with open(path, "w", encoding="utf-8", newline="") as f:
                f.write(output)
        except Exception as exc:
            self.app.notify(title="Export failed", message=str(exc), severity="error")
            return
        self.app.notify(
            title="Export complete",
            message=f"Wrote {path}.",
            severity="success",
            timeout=4,
        )

    def _action_import_records(self) -> None:
        import_form = Form(
            fields=[
                FormField(
                    title="Path",
                    key="path",
                    type="string",
                    placeholder="Path to import CSV",
                )
            ]
        )
        self.app.push_screen(
            InputModal("Import records from CSV", form=import_form),
            callback=self._run_import_records,
        )

    def _run_import_records(self, result) -> None:
        if not result:
            return
        path = result["path"]
        try:
            with open(path, "r", encoding="utf-8") as f:
                csv_text = f.read()
            rows = import_records_from_csv(csv_text)
            imported = 0
            for row in rows:
                record_data = {
                    "date": row["date"],
                    "label": row["label"],
                    "amount": float(row["amount"]),
                    "isIncome": bool(int(row["isIncome"])),
                    "isTransfer": bool(int(row.get("isTransfer", 0))),
                }
                if row["account"]:
                    account = self._find_account_by_name(row["account"])
                    if account:
                        record_data["accountId"] = account.id
                    else:
                        raise ValueError(f"Account not found: {row['account']}")
                if row["category"]:
                    category = self._find_category_by_name(row["category"])
                    if category:
                        record_data["categoryId"] = category.id
                    else:
                        raise ValueError(f"Category not found: {row['category']}")
                create_record(record_data)
                imported += 1
        except Exception as exc:
            self.app.notify(title="Import failed", message=str(exc), severity="error")
            return
        self.app.notify(
            title="Import complete",
            message=f"Imported {imported} records from {path}.",
            severity="success",
            timeout=4,
        )

    def _find_account_by_name(self, name: str):
        from bagels.managers.accounts import get_all_accounts

        lower_name = name.strip().lower()
        for account in get_all_accounts(get_hidden=True):
            if account.name.strip().lower() == lower_name:
                return account
        return None

    def _find_category_by_name(self, name: str):
        from bagels.managers.categories import get_all_categories_tree

        lower_name = name.strip().lower()
        for category, _, _ in get_all_categories_tree():
            if category.name.strip().lower() == lower_name:
                return category
        return None

    def _action_toggle_update_check(self) -> None:
        cur = config.CONFIG.state.check_for_updates
        write_state("check_for_updates", not cur)
        self.app.notify(
            f"Update check {'enabled' if not cur else 'disabled'} on startup"
        )

    def _action_open_config_file(self) -> None:
        try:
            file = config_file()
            if platform.system() == "Darwin":  # macOS
                subprocess.call(("open", file))
            elif platform.system() == "Windows":  # Windows
                subprocess.call(("start", file), shell=True)
            else:  # Linux and other Unix-like systems
                subprocess.call(("xdg-open", file))
            self.app.exit(message="Opened config file in default editor!")
        except Exception as e:
            self.app.notify(
                f"Failed to open config file: {e}", title="Error", severity="error"
            )

    def _action_toggle_footer(self) -> None:
        cur = config.CONFIG.state.footer_visibility
        write_state("footer_visibility", not cur)
        self.app.refresh(layout=True, recompose=True)
        self.app.notify(f"Footer {'enabled' if not cur else 'disabled'}")

