from textual.app import ComposeResult
from textual.containers import Container, ScrollableContainer
from textual.widgets import (
    Footer,
)

from bagels.components.header import Header


class ModalContainer(ScrollableContainer, can_focus=False):
    # usage: ModalContainer(w1, w2, w3..... hotkeys=[])
    def __init__(self, *content, custom_classes: str = "wrapper base-modal"):
        super().__init__(classes=custom_classes)
        self.content = content
        # self.hotkeys = hotkeys

    def compose(self) -> ComposeResult:
        yield Header(
            show_clock=False,
            icon="x",
            icon_action="app.pop_screen",
            icon_tooltip="Close",
        )
        with Container(classes="container"):
            for widget in self.content:
                yield widget
        yield Footer(show_command_palette=False)
