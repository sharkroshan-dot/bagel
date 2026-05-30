from pydantic import BaseModel
from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Label, Static


class BarchartData(BaseModel):
    amounts: list[float]
    labels: list[str]


class Barchart(Static):
    DEFAULT_CSS = """
    Barchart {
        width: 1fr;
        height: auto;

        & > .data-container {
            layout: horizontal;
            height: auto;

            .labels-container {
                height: auto;
                width: 5;
                color: $text-muted;
                border-right: wide $accent-lighten-3;
                background: $surface;
                
                .label {
                    width: 1fr;
                }
            }

            .bars-container {
            background: transparent;
            height: auto;

                .bar-container {
                    height: 1;
                    width: 100%;
                    background: $surface;
                    
                    .bar {
                        background: $surface-lighten-2;
                        min-width: 1;
                        border-top: tall $surface-lighten-3;
                    }
                }
            }
        }

        .max-amount {
            color: $text-muted;
            text-align: right;
            width: 1fr;
        }
    }
    """

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.data = BarchartData(amounts=[], labels=[])
        self.last_count = 0

    def on_mount(self) -> None:
        self.rebuild()

    def set_data(self, data: BarchartData) -> None:
        self.data = data
        self.rebuild()

    def rebuild(self):
        if len(self.data.amounts) == 0:
            self.styles.display = "none"
            return
        else:
            self.styles.display = "block"

        max_amount = max(self.data.amounts)
        self.query_one(".max-amount").update(f"{max_amount}")

        # If count changed, do full rebuild
        if len(self.data.amounts) != self.last_count:
            # Clear existing bars and labels
            bars_container = self.query(".bars-container")
            if bars_container:
                bars_container[0].remove()

            labels_container = self.query(".labels-container")
            if labels_container:
                labels_container[0].remove()

            bars_container = Container(classes="bars-container")
            labels_container = Container(classes="labels-container")

            for i in range(len(self.data.amounts)):
                amount = self.data.amounts[i]
                label = self.data.labels[i]
                percentage = (amount / max_amount * 100) if max_amount > 0 else 0
                # build bar
                bar_container = Container(classes="bar-container")
                bar = Static(" ", classes="bar")
                bar.styles.width = f"{percentage}%"
                bar_container.compose_add_child(bar)
                bars_container.compose_add_child(bar_container)
                # build label
                label_widget = Label(label, classes="label")
                labels_container.compose_add_child(label_widget)

            data_container = self.query_one(".data-container")
            data_container.mount(labels_container)
            data_container.mount(bars_container)

            self.last_count = len(self.data.amounts)

        else:
            # Just update existing widgets
            bars = self.query(".bar")
            labels = self.query(".label")

            for i in range(len(self.data.amounts)):
                amount = self.data.amounts[i]
                label = self.data.labels[i]
                percentage = (amount / max_amount * 100) if max_amount > 0 else 0

                bars[i].styles.width = f"{percentage}%"
                labels[i].update(label)

    def compose(self) -> ComposeResult:
        # Create containers
        yield Label("Loading...", classes="max-amount")
        yield Container(classes="data-container")
