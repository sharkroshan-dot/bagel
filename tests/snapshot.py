import pytest

import os
import time_machine
import datetime as dt
from zoneinfo import ZoneInfo

from textual.pilot import Pilot

hill_valley_tz = ZoneInfo("America/Los_Angeles")

TEMP_INSTANCE_PATH = os.path.join(os.path.dirname(__file__), "../instance/")
SIZE_BASIC = (140, 30)
SIZE_VERTICAL = (70, 50)
SIZE_TEST = (140, 30)
APP_PARAMS = {"is_testing": True}


# ---------- Clear last test --------- #

if os.path.exists(TEMP_INSTANCE_PATH):
    for file in os.listdir(TEMP_INSTANCE_PATH):
        os.remove(os.path.join(TEMP_INSTANCE_PATH, file))

# --------- Init app sequence -------- #
from bagels.locations import set_custom_root

set_custom_root(TEMP_INSTANCE_PATH)

from bagels.config import load_config

load_config()

from bagels.models.database.app import init_db

init_db()

from bagels.app import App

# -------------- Freeze -------------- #


@pytest.fixture(autouse=True)
def travel_to_hill_valley_time():
    with time_machine.travel(dt.datetime(1985, 10, 26, 1, 24, tzinfo=hill_valley_tz)):
        yield  # This allows the tests to run within the context of the travel


# --------------- Basic -------------- #


class TestBasic:
    def test_1_welcome(self, snap_compare):
        assert snap_compare(App(**APP_PARAMS), terminal_size=SIZE_BASIC)

    def test_2_new_acc_welcome(self, snap_compare):
        async def r(pilot: Pilot):
            await pilot.press("a")  # add
            await pilot.press("t", "tab")  # name
            await pilot.press(*"123.45", "enter")  # value

        assert snap_compare(App(**APP_PARAMS), terminal_size=SIZE_BASIC, run_before=r)

    def test_3_vertical_layout(self, snap_compare):
        assert snap_compare(
            App(**APP_PARAMS),
            terminal_size=SIZE_VERTICAL,
        )

    def test_4_jump_screen(self, snap_compare):
        assert snap_compare(
            App(**APP_PARAMS),
            terminal_size=SIZE_BASIC,
            press=["v"],
        )


# ------------- Accounts ------------- #


class TestAccounts:
    def test_5_acc_screen(self, snap_compare):
        assert snap_compare(App(**APP_PARAMS), terminal_size=SIZE_TEST, press=["a"])

    def test_6_new_acc_home(self, snap_compare):
        async def r(pilot: Pilot):
            await pilot.press("v", "a")  # jump to accounts
            await pilot.wait_for_animation()
            await pilot.press("a")  # add
            await pilot.press(*"t2", "enter")  # name

        assert snap_compare(
            App(**APP_PARAMS),
            terminal_size=SIZE_TEST,
            run_before=r,
        )

    def test_7_delete_acc(self, snap_compare):
        async def r(pilot: Pilot):
            await pilot.press("v", "a")  # jump to accounts
            await pilot.press("d", "enter")  # delete

        assert snap_compare(
            App(**APP_PARAMS),
            terminal_size=SIZE_TEST,
            run_before=r,
        )

    def test_8_edit_acc(self, snap_compare):
        async def r(pilot: Pilot):
            await pilot.press("v", "a")  # jump to accounts
            await pilot.press("e")  # edit
            await pilot.press("tab", *"123.234", "enter")  # edit beg. balance

        assert snap_compare(
            App(**APP_PARAMS),
            terminal_size=SIZE_TEST,
            run_before=r,
        )


# ------------ Categories ------------ #


class TestCategories:
    def test_9_categories(self, snap_compare):
        assert snap_compare(
            App(**APP_PARAMS),
            terminal_size=SIZE_TEST,
            press=["c"],
        )

    def test_10_new_category_screen(self, snap_compare):
        assert snap_compare(
            App(**APP_PARAMS),
            terminal_size=SIZE_TEST,
            press=["c", "a"],
        )

    def test_11_new_category(self, snap_compare):
        async def r(pilot: Pilot):
            await pilot.press("c")  # show categories modal
            await pilot.press("a")  # add
            await pilot.press("t", "tab")  # name
            await pilot.press("tab", "tab", "enter")  # nature, color, save

        # todo: scroll to bottom
        assert snap_compare(
            App(**APP_PARAMS),
            terminal_size=SIZE_TEST,
            run_before=r,
        )

    def test_12_new_category_subcategory(self, snap_compare):
        async def r(pilot: Pilot):
            await pilot.press("c")  # show categories modal
            await pilot.press("up")  # select last created
            await pilot.press("s")  # add subcategory
            await pilot.press("t", "tab")  # name
            await pilot.press("tab", "tab", "enter")  # nature, color, save

        assert snap_compare(
            App(**APP_PARAMS),
            terminal_size=SIZE_TEST,
            run_before=r,
        )

    def test_13_delete_category(self, snap_compare):
        async def r(pilot: Pilot):
            await pilot.press("c")  # show categories modal
            await pilot.press("d", "enter")  # delete

        assert snap_compare(
            App(**APP_PARAMS),
            terminal_size=SIZE_TEST,
            run_before=r,
        )


# ------------- Templates ------------ #


class TestTemplates:
    def test_14_templates(self, snap_compare):
        async def r(pilot: Pilot):
            await pilot.press("v", "t")  # jump to templates
            await pilot.press("a")  # add
            await pilot.press("t", "tab")  # name
            await pilot.press("tab")  # category
            await pilot.press(*"123")  # enter value
            await pilot.press("tab")  # account
            await pilot.press("tab", "space", "enter")  # switch to income, save

        assert snap_compare(
            App(**APP_PARAMS),
            terminal_size=SIZE_TEST,
            run_before=r,
        )

    def test_15_edit_template(self, snap_compare):
        async def r(pilot: Pilot):
            await pilot.press("v", "t")  # jump to templates
            await pilot.press("tab")  # select first template
            await pilot.press("e")  # edit
            await pilot.press(*"est")  # edit name
            await pilot.press("enter")  # save

        assert snap_compare(
            App(**APP_PARAMS),
            terminal_size=SIZE_TEST,
            run_before=r,
        )
