from abc import ABC, abstractmethod
from datetime import datetime
from functools import lru_cache

import numpy as np

from bagels.components.tplot.plot import Plot
import bagels.config as config
from bagels.managers.records import (
    get_daily_balance,
    get_spending,
    get_spending_trend,
)
from bagels.managers.utils import get_income_to_use


class BasePlot(ABC):
    name: str = "Base Plot"
    supports_cross_periods: bool = False

    def __init__(self, app):
        self.app = app

    @abstractmethod
    def get_data(
        self, start_of_period: datetime, end_of_period: datetime
    ) -> list[float]:
        """Return a list of data points"""
        pass

    @abstractmethod
    def plot(
        self,
        plt: Plot,
        start_of_period: datetime,
        end_of_period: datetime,
        offset: int,
        data: list[float],
        dates: list[str],
        get_theme_color,
    ) -> None:
        """Additional operations on the plotext object."""
        pass


class SpendingPlot(BasePlot):
    name: str = "Spending"

    @lru_cache
    def get_data(self, start_of_period, end_of_period):
        return get_spending(start_of_period, end_of_period)

    def plot(
        self,
        plt: Plot,
        start_of_period: datetime,
        end_of_period: datetime,
        offset: int,
        data: list[float],
        dates: list[str],
        get_theme_color,
    ) -> None:
        if min(data) >= 0:
            plt.ylim(lower=0)


class SpendingTrajectoryPlot(BasePlot):
    name: str = "Spending Trajectory"

    @lru_cache
    def get_data(self, start_of_period, end_of_period):
        return get_spending_trend(start_of_period, end_of_period)

    def plot(
        self,
        plt: Plot,
        start_of_period: datetime,
        end_of_period: datetime,
        offset: int,
        data: list[float],
        dates: list[str],
        get_theme_color,
    ) -> None:
        # --------- Limit computation -------- #

        limit = get_income_to_use(offset)

        plt.ylim(upper=limit, lower=0)

        if len(data) == len(dates):
            return  # don't have to show regression prediction trend

        # ---------- Prediction line --------- #

        # Estimate data trend by creating an array of length len(dates) - len(data), filled with values from linear regression.
        # Plot the data by using reversed dates to put at the right hand side of the plot
        if len(data) >= 2:
            x = np.arange(len(data))
            coefficients = np.polyfit(x, data, 1)
            trend = np.poly1d(coefficients)

            # Generate prediction points for the remaining days
            remaining_days = len(dates) - len(data)
            if remaining_days > 0:
                prediction_x = np.arange(len(data), len(dates))
                prediction_y = trend(prediction_x)
                prediction_data = data + prediction_y.tolist()

                plt.plot(
                    dates,
                    prediction_data,
                    marker=config.CONFIG.defaults.plot_marker,
                    color=get_theme_color("secondary"),
                )

        # ----- Period spending separator ---- #

        period_spending = max(data)

        total_days = (end_of_period - start_of_period).days + 1

        plt.plot(
            dates,
            [period_spending] * total_days,
            marker=config.CONFIG.defaults.plot_marker,
            color=get_theme_color("panel"),
        )


class BalancePlot(BasePlot):
    name: str = "Balance"
    supports_cross_periods = True

    @lru_cache
    def get_data(self, start_of_period, end_of_period):
        return get_daily_balance(start_of_period, end_of_period)

    def plot(
        self,
        plt: Plot,
        start_of_period: datetime,
        end_of_period: datetime,
        offset: int,
        data: list[float],
        dates: list[str],
        get_theme_color,
    ) -> None:
        pass

