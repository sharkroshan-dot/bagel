from argparse import ArgumentParser
from datetime import datetime
from pathlib import Path

import aiohttp_jinja2
import jinja2
from aiohttp import web

from bagels.locations import set_custom_root
from bagels.config import load_config
from bagels.managers.accounts import create_account, get_all_accounts_with_balance
from bagels.managers.categories import get_all_categories_tree
from bagels.managers.records import create_record, get_records
from bagels.models.database.app import init_db


def serialize_account(account):
    return {
        "id": account.id,
        "name": account.name,
        "description": account.description,
        "balance": float(account.balance),
    }


def serialize_category(category):
    return {
        "id": category.id,
        "name": category.name,
        "nature": category.nature.value if category.nature else None,
        "color": category.color,
        "parent": category.parentCategory.name if category.parentCategory else None,
    }


def serialize_record(record):
    return {
        "id": record.id,
        "label": record.label,
        "amount": float(record.amount),
        "date": record.date.strftime("%Y-%m-%d"),
        "isIncome": bool(record.isIncome),
        "isTransfer": bool(record.isTransfer),
        "category": record.category.name if record.category else None,
        "account": record.account.name if record.account else None,
        "transferToAccount": record.transferToAccount.name if record.transferToAccount else None,
    }


async def index(request: web.Request) -> web.Response:
    accounts = [serialize_account(acc) for acc in get_all_accounts_with_balance()]
    categories = [serialize_category(category) for category, _, _ in get_all_categories_tree()]
    records = [serialize_record(record) for record in get_records(offset_type="all")][:20]

    return aiohttp_jinja2.render_template(
        "index.html",
        request,
        {
            "accounts": accounts,
            "categories": categories,
            "records": records,
        },
    )


async def api_accounts(request: web.Request) -> web.Response:
    accounts = [serialize_account(acc) for acc in get_all_accounts_with_balance()]
    return web.json_response({"accounts": accounts})


async def api_categories(request: web.Request) -> web.Response:
    categories = [serialize_category(category) for category, _, _ in get_all_categories_tree()]
    return web.json_response({"categories": categories})


async def api_records(request: web.Request) -> web.Response:
    records = [serialize_record(record) for record in get_records(offset_type="all")]
    return web.json_response({"records": records})


async def create_account_handler(request: web.Request) -> web.Response:
    data = await request.post()
    name = (data.get("name") or "").strip()
    if not name:
        raise web.HTTPBadRequest(text="Account name is required.")

    beginning_balance_raw = (data.get("beginningBalance") or "0").strip()
    try:
        beginning_balance = float(beginning_balance_raw)
    except ValueError as exc:
        raise web.HTTPBadRequest(text="Beginning balance must be a number.") from exc

    create_account(
        {
            "name": name,
            "description": (data.get("description") or "").strip(),
            "beginningBalance": beginning_balance,
        }
    )
    raise web.HTTPFound("/")


async def create_record_handler(request: web.Request) -> web.Response:
    data = await request.post()
    label = (data.get("label") or "").strip()
    if not label:
        raise web.HTTPBadRequest(text="Record label is required.")

    amount_raw = (data.get("amount") or "").strip()
    account_id_raw = (data.get("accountId") or "").strip()
    category_id_raw = (data.get("categoryId") or "").strip()
    date_raw = (data.get("date") or "").strip()

    try:
        amount = float(amount_raw)
    except ValueError as exc:
        raise web.HTTPBadRequest(text="Amount must be a number.") from exc

    try:
        account_id = int(account_id_raw)
    except ValueError as exc:
        raise web.HTTPBadRequest(text="Please select a valid account.") from exc

    if not date_raw:
        date_value = datetime.now()
    else:
        try:
            date_value = datetime.fromisoformat(date_raw)
        except ValueError as exc:
            raise web.HTTPBadRequest(text="Date must be YYYY-MM-DD.") from exc

    create_record(
        {
            "label": label,
            "amount": amount,
            "date": date_value,
            "isIncome": data.get("isIncome") == "on",
            "isTransfer": False,
            "accountId": account_id,
            "categoryId": int(category_id_raw) if category_id_raw else None,
            "transferToAccountId": None,
        }
    )
    raise web.HTTPFound("/")


def create_app(data_root: Path | None = None) -> web.Application:
    if data_root:
        set_custom_root(data_root)

    # Load configuration (creates CONFIG) before initializing DB and handlers
    load_config()

    init_db()

    package_dir = Path(__file__).resolve().parent
    app = web.Application()

    aiohttp_jinja2.setup(
        app,
        loader=jinja2.FileSystemLoader(package_dir / "templates"),
    )

    app.router.add_static(
        "/static/",
        path=package_dir / "static",
        name="static",
    )
    app.router.add_get("/", index)
    app.router.add_get("/api/accounts", api_accounts)
    app.router.add_get("/api/categories", api_categories)
    app.router.add_get("/api/records", api_records)
    app.router.add_post("/accounts/create", create_account_handler)
    app.router.add_post("/records/create", create_record_handler)

    return app


def main() -> None:
    parser = ArgumentParser(description="Run the Bagels web frontend.")
    parser.add_argument("--at", help="Custom root path for Bagels data.")
    parser.add_argument("--host", default="127.0.0.1", help="Host to bind the web server.")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind the web server.")
    args = parser.parse_args()

    app = create_app(Path(args.at) if args.at else None)
    web.run_app(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()

