from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import MarkdownViewer, Static

from bagels.components.bagel import Bagel


class Welcome(Static):
    can_focus = True

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs, id="welcome-container")
        file_path = Path(__file__).parent.parent.parent / "static" / "welcome.md"
        with open(file_path, "r") as file:
            self.welcome_text = file.read()

    def compose(self) -> ComposeResult:
        with Container(classes="text-container"):
            yield MarkdownViewer(self.welcome_text, show_table_of_contents=False)
        yield Bagel()
