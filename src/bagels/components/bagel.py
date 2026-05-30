from textual.app import ComposeResult
from textual.widgets import Label, Static

from bagels.bagel import get_string, phi_spacing, render_frame, theta_spacing


class Bagel(Static):
    A = B = 1

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs, classes="bagel-container")

    def on_mount(self) -> None:
        if not self.app.is_testing:
            self.set_interval(1 / 10, self.update_bagel)
        else:
            self.update_bagel()

    def update_bagel(self) -> None:
        bagel = self.query_one("#bagel")
        self.A += theta_spacing
        self.B += phi_spacing
        bagel.update(get_string(render_frame(self.A, 1)))

    def compose(self) -> ComposeResult:
        yield Label(id="bagel")
