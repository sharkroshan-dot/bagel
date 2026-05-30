from datetime import datetime, timedelta

import dateutil
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.reactive import Reactive, reactive
from textual.widgets import Button, Label, Static

from bagels.components.indicators import EmptyIndicator
from bagels.components.modules.spending.plots import (
    BalancePlot,
    SpendingPlot,
    SpendingTrajectoryPlot,
)
from bagels.components.tplot import PlotextPlot
from bagels.components.tplot.plot import rgbify_hex
import bagels.config as config
from bagels.managers.utils import get_start_end_of_period
from bagels.utils.format import format_period_to_readable


class Spending(Static):
    PLOT_TYPES = [SpendingTrajectoryPlot, SpendingPlot, BalancePlot]

    can_focus = True
    periods: Reactive[int] = reactive(1)
    current_plot: Reactive[int] = reactive(0)

    BINDINGS = [
        Binding("+", "zoom_in", "Zoom in", show=True),
        Binding("-", "zoom_out", "Zoom out", show=True),
    ]

    def __init__(self, page_parent: Static, *args, **kwargs) -> None:
        super().__init__(
            *args, **kwargs, id="spending-container", classes="module-container"
        )
        super().__setattr__("border_title", "Spending")
        self._plots = [plot_cls(self.app) for plot_cls in self.PLOT_TYPES]
        self.page_parent = page_parent

    def on_mount(self) -> None:
        self.rebuild()
        self.app.theme_changed_signal2.subscribe(self, lambda theme: self.rebuild())
        self.query(Button)[4].focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "inc-offset":
            self.page_parent.action_inc_offset()
        elif event.button.id == "dec-offset":
            self.page_parent.action_dec_offset()
        elif event.button.id == "zoom-in":
            self.action_zoom_in()
        elif event.button.id == "zoom-out":
            self.action_zoom_out()
        elif event.button.id.startswith("plot-"):
            try:
                plot_index = int(event.button.id.split("-")[1])
                self.current_plot = plot_index
                self.query_one(".selected").set_classes("")
                event.button.set_classes("selected")
                self.rebuild()
            except ValueError:
                pass

    def rebuild(self) -> None:
        empty = self.query_one(EmptyIndicator)
        plotext = self.query_one(PlotextPlot)
        zoom_in_button = self.query_one("#zoom-in")
        zoom_out_button = self.query_one("#zoom-out")
        label = self.query_one(".current-view-label")
        plotext.display = False  # make plotext update by toggling display... for some reason. Maybe a bug? Who knows.
        plot = self._plots[self.current_plot]

        start_of_period, end_of_period = get_start_end_of_period(
            self.page_parent.offset, "month"
        )
        self.app.log(
            f"The plot type {plot.name} has support for cross periods: {plot.supports_cross_periods}"
        )

        # ----------- Cross period ----------- #

        self.app.log(
            f'Getting spending trend from "{start_of_period}" to "{end_of_period} ({self.page_parent.offset} months ago)"'
        )
        string = format_period_to_readable(
            {"offset": self.page_parent.offset, "offset_type": "month"}
        )

        if plot.supports_cross_periods:
            start_of_period = start_of_period - dateutil.relativedelta.relativedelta(
                months=self.periods - 1
            )
            zoom_in_button.display = True
            zoom_out_button.display = True
            if self.periods == 1:
                label.update(string)
            else:
                label.update(
                    f"{string} to {format_period_to_readable({'offset': self.page_parent.offset - self.periods + 1, 'offset_type': 'month'})}"
                )
        else:
            zoom_in_button.display = False
            zoom_out_button.display = False
            label.update(string)

        plt = self.query_one(PlotextPlot).plt
        plt.clear_data()
        plt.clear_figure()

        # ------------- get data ------------- #

        data = plot.get_data(start_of_period, end_of_period)
        total_days = (
            end_of_period - start_of_period
        ).days + 1  # add one to include the end date
        correct_data = len(data) > 0
        empty.display = not correct_data
        plotext.display = correct_data
        if not correct_data:
            return

        # --------------- plot --------------- #

        bagel_theme = self.app.themes[self.app.app_theme]

        def get_theme_color(key):
            return (
                rgbify_hex(getattr(bagel_theme, key, None))
                if getattr(bagel_theme, key, None) is not None
                else rgbify_hex(self.app.theme_variables[key])
            )

        dates = [
            (start_of_period + timedelta(days=i)).strftime("%d/%m/%Y")
            for i in range(total_days)
        ]

        plot.plot(
            plt,
            start_of_period,
            end_of_period,
            self.page_parent.offset,
            data,
            dates,
            get_theme_color,
        )

        plt.plot(
            dates,
            data,
            marker=config.CONFIG.defaults.plot_marker,
            color=get_theme_color("accent"),
        )

        # -------------- styling ------------- #

        plt.date_form(output_form="d")
        plt.xfrequency(total_days)
        plt.xlim(dates[0], dates[-1])

        today = datetime.now()
        line_color = get_theme_color("panel")
        fdow_line_color = get_theme_color("secondary")
        today_line_color = get_theme_color("success")

        if plot.supports_cross_periods and self.periods > 1:

            def compare_function(dd):
                return dd.day == 1
        else:

            def compare_function(dd):
                return dd.weekday() == config.CONFIG.defaults.first_day_of_week

        for d in dates:
            d_datetime = datetime.strptime(d, "%d/%m/%Y")
            if d_datetime.date() == today.date():
                plt.vline(d, today_line_color)
            elif compare_function(d_datetime):
                plt.vline(d, fdow_line_color)
            else:
                plt.vline(d, line_color)

        plt.xaxes(False)
        plt.yaxes(False)

    def check_supports_cross_periods(self) -> bool:
        if not self._plots[self.current_plot].supports_cross_periods:
            self.app.notify(
                "Current plot does not this operation.",
                title="Cross periods not supported",
                severity="information",
            )
            return False
        return True

    def action_zoom_in(self) -> None:
        if not self.check_supports_cross_periods():
            return
        self.periods = self.periods - 1 if self.periods > 1 else 1
        self.rebuild()

    def action_zoom_out(self) -> None:
        if not self.check_supports_cross_periods():
            return
        self.periods = self.periods + 1 if self.periods < 12 else 12
        self.rebuild()

    def compose(self) -> ComposeResult:
        with Horizontal(id="top-controls-container"):
            yield Button("+", id="zoom-in")
            yield Button("<<<", id="dec-offset")
            yield Label("UPDATEME", classes="current-view-label")
            yield Button(">>>", id="inc-offset")
            yield Button("-", id="zoom-out")
        yield PlotextPlot()
        yield EmptyIndicator("No data to display")
        with Horizontal(id="bottom-controls-container"):
            for i, plot in enumerate(self._plots):
                button_classes = "selected" if i == self.current_plot else ""
                yield Button(plot.name, id=f"plot-{i}", classes=button_classes)
                if i != len(self._plots) - 1:
                    yield Label(" | ")

