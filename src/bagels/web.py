from argparse import ArgumentParser
from datetime import datetime, timedelta
from pathlib import Path

import aiohttp_jinja2
import jinja2
from aiohttp import web

from bagels.locations import set_custom_root
from bagels.config import load_config
from bagels.managers.accounts import (
    create_account,
    delete_account,
    get_all_accounts_with_balance,
    update_account,
)
from bagels.managers.categories import (
    create_category,
    delete_category,
    get_all_categories_tree,
    update_category,
)
from bagels.managers.records import (
    create_record,
    delete_record,
    export_category_report_to_csv,
    export_records_to_csv,
    get_deleted_records,
    get_records,
    import_records_from_csv,
    restore_record,
    update_record,
)
from bagels.models.category import Nature
from bagels.models.database.app import init_db


def serialize_account(account):
    return {
        "id": account.id,
        "name": account.name,
        "description": account.description,
        "beginningBalance": float(account.beginningBalance),
        "balance": float(account.balance),
    }


def serialize_category(category):
    return {
        "id": category.id,
        "name": category.name,
        "nature": category.nature.value if category.nature else None,
        "natureKey": category.nature.name if category.nature else None,
        "color": category.color,
        "parentId": category.parentCategoryId,
        "parent": category.parentCategory.name if category.parentCategory else None,
    }


def serialize_record(record):
    return {
        "id": record.id,
        "label": record.label,
        "amount": float(record.amount),
        "date": record.date.strftime("%Y-%m-%d"),
        "accountId": record.accountId,
        "categoryId": record.categoryId,
        "isIncome": bool(record.isIncome),
        "isTransfer": bool(record.isTransfer),
        "category": record.category.name if record.category else None,
        "account": record.account.name if record.account else None,
        "transferToAccount": record.transferToAccount.name if record.transferToAccount else None,
    }


def _build_redirect_url(account_id: int | None = None) -> str:
    if account_id:
        return f"/?account_id={account_id}"
    return "/"


def _parse_optional_account_id(raw: str | None) -> int | None:
    if not raw:
        return None
    try:
        return int(raw.strip())
    except (TypeError, ValueError):
        return None


async def index(request: web.Request) -> web.Response:
    selected_account_id = _parse_optional_account_id(request.query.get("account_id"))
    account_query = (request.query.get("account_q") or "").strip()
    category_query = (request.query.get("category_q") or "").strip()
    record_query = (request.query.get("record_q") or "").strip()
    imported_flag = request.query.get("imported")
    import_error = request.query.get("import_error")
    all_accounts = [serialize_account(acc) for acc in get_all_accounts_with_balance()]
    accounts = list(all_accounts)
    if account_query:
        needle = account_query.lower()
        accounts = [
            acc
            for acc in accounts
            if needle in (acc["name"] or "").lower()
            or needle in (acc["description"] or "").lower()
        ]
    categories = [serialize_category(category) for category, _, _ in get_all_categories_tree()]
    if category_query:
        needle = category_query.lower()
        categories = [
            cat
            for cat in categories
            if needle in (cat["name"] or "").lower()
            or needle in (cat["nature"] or "").lower()
            or needle in (cat["parent"] or "").lower()
        ]
    records = [
        serialize_record(record)
        for record in get_records(offset_type="all", account_id=selected_account_id)
    ][:20]
    if record_query:
        needle = record_query.lower()
        records = [
            rec
            for rec in records
            if needle in (rec["label"] or "").lower()
            or needle in (rec["account"] or "").lower()
            or needle in (rec["category"] or "").lower()
            or needle in str(rec["amount"]).lower()
            or needle in (rec["date"] or "").lower()
        ]

    deleted_records = [serialize_record(record) for record in get_deleted_records()]

    all_month_records = get_records(offset_type="month")
    all_week_records = get_records(offset_type="week")
    month_spend = sum(
        record.amount
        for record in all_month_records
        if not record.isIncome and not record.isTransfer
    )
    week_spend = sum(
        record.amount
        for record in all_week_records
        if not record.isIncome and not record.isTransfer
    )
    month_income = sum(
        record.amount
        for record in all_month_records
        if record.isIncome and not record.isTransfer
    )
    net_flow = month_income - month_spend
    category_totals = {}
    for record in all_month_records:
        if record.isIncome or record.isTransfer:
            continue
        category_name = record.category.name if record.category else "Uncategorized"
        category_totals[category_name] = category_totals.get(category_name, 0.0) + record.amount
    top_category = None
    if category_totals:
        top_category = max(category_totals.items(), key=lambda item: item[1])[0]

    account_spend_records = {}
    for account in all_accounts:
        spend_rows = [
            serialize_record(record)
            for record in get_records(offset_type="all", account_id=account["id"])
            if not record.isIncome
        ][:20]
        account_spend_records[account["id"]] = spend_rows
    selected_account = next(
        (account for account in all_accounts if account["id"] == selected_account_id), None
    )

    if selected_account:
        manage_accounts = [selected_account]
    else:
        manage_accounts = all_accounts

    return aiohttp_jinja2.render_template(
        "index.html",
        request,
        {
            "accounts": accounts,
            "all_accounts": all_accounts,
            "categories": categories,
            "records": records,
            "deleted_records": deleted_records,
            "account_spend_records": account_spend_records,
            "nature_options": [nature.name for nature in Nature],
            "account_query": account_query,
            "category_query": category_query,
            "record_query": record_query,
            "selected_account_id": selected_account_id,
            "selected_account": selected_account,
            "manage_accounts": manage_accounts,
            "imported_flag": imported_flag,
            "import_error": import_error,
            "dashboard": {
                "week_spend": round(week_spend, 2),
                "month_spend": round(month_spend, 2),
                "net_flow": round(net_flow, 2),
                "top_category": top_category,
            },
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


async def account_records_page(request: web.Request) -> web.Response:
    account_id = int(request.match_info["account_id"])
    all_accounts = [serialize_account(acc) for acc in get_all_accounts_with_balance()]
    account = next((acc for acc in all_accounts if acc["id"] == account_id), None)
    if not account:
        raise web.HTTPNotFound(text="Account not found.")

    records = [
        serialize_record(record)
        for record in get_records(offset_type="all", account_id=account_id)
    ]
    categories = [serialize_category(category) for category, _, _ in get_all_categories_tree()]
    return aiohttp_jinja2.render_template(
        "account_records.html",
        request,
        {
            "account": account,
            "records": records,
            "all_accounts": all_accounts,
            "categories": categories,
        },
    )


def _parse_boolean(raw: str | None) -> bool:
    return str(raw or "").strip().lower() in {"1", "true", "yes", "on"}


def _find_named_item_id(name: str | None, items: list[dict], default_key: str = "name") -> int | None:
    if not name:
        return None
    normalized = name.strip().lower()
    for item in items:
        if item.get(default_key, "").strip().lower() == normalized:
            return item.get("id")
    return None


async def export_records_handler(request: web.Request) -> web.Response:
    account_id = _parse_optional_account_id(request.query.get("account_id"))
    offset_type = request.query.get("offset_type") or "all"
    csv_data = export_records_to_csv(offset_type=offset_type, account_id=account_id)
    headers = {
        "Content-Type": "text/csv",
        "Content-Disposition": "attachment; filename=bagels-records.csv",
    }
    return web.Response(text=csv_data, headers=headers)


async def export_category_report_handler(request: web.Request) -> web.Response:
    offset_type = request.query.get("offset_type") or "month"
    csv_data = export_category_report_to_csv(offset_type=offset_type)
    headers = {
        "Content-Type": "text/csv",
        "Content-Disposition": "attachment; filename=bagels-category-report.csv",
    }
    return web.Response(text=csv_data, headers=headers)


async def import_records_handler(request: web.Request) -> web.Response:
    reader = await request.multipart()
    part = await reader.next()
    while part is not None and part.name != "records_csv":
        part = await reader.next()
    if part is None:
        raise web.HTTPBadRequest(text="CSV file upload is required.")

    csv_bytes = await part.read(decode=True)
    raw_text = csv_bytes.decode("utf-8", errors="replace")
    rows = import_records_from_csv(raw_text)
    all_accounts = [serialize_account(acc) for acc in get_all_accounts_with_balance()]
    all_categories = [serialize_category(category) for category, _, _ in get_all_categories_tree()]

    imported = 0
    for row in rows:
        label = (row.get("label") or "").strip()
        amount_raw = (row.get("amount") or "").strip()
        if not label or not amount_raw:
            continue

        try:
            amount = float(amount_raw)
        except ValueError:
            continue

        account_id = _find_named_item_id(row.get("account"), all_accounts)
        if account_id is None and all_accounts:
            account_id = all_accounts[0]["id"]

        category_id = _find_named_item_id(row.get("category"), all_categories)

        if account_id is None:
            continue

        date_value = datetime.now()
        if row.get("date"):
            try:
                date_value = datetime.fromisoformat(row["date"].strip())
            except ValueError:
                pass

        create_record(
            {
                "label": label,
                "amount": amount,
                "date": date_value,
                "isIncome": _parse_boolean(row.get("isIncome")),
                "isTransfer": False,
                "accountId": account_id,
                "categoryId": category_id,
                "transferToAccountId": None,
            }
        )
        imported += 1

    raise web.HTTPFound(f"/?imported={imported}")


async def restore_record_handler(request: web.Request) -> web.Response:
    data = await request.post()
    record_id = int((data.get("id") or "0").strip())
    restore_record(record_id)
    return_to = (data.get("return_to") or "").strip()
    if return_to.startswith("/"):
        raise web.HTTPFound(return_to)
    raise web.HTTPFound("/")


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
    return_account_id = _parse_optional_account_id((data.get("return_account_id") or "").strip())
    raise web.HTTPFound(_build_redirect_url(return_account_id))


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
    return_account_id = _parse_optional_account_id((data.get("return_account_id") or "").strip())
    raise web.HTTPFound(_build_redirect_url(return_account_id or account_id))


def _parse_nature(nature_raw: str | None) -> Nature:
    if not nature_raw:
        raise web.HTTPBadRequest(text="Category nature is required.")
    key = nature_raw.strip().upper()
    try:
        return Nature[key]
    except KeyError as exc:
        allowed = ", ".join(n.name for n in Nature)
        raise web.HTTPBadRequest(text=f"Invalid nature. Use one of: {allowed}") from exc


async def create_category_handler(request: web.Request) -> web.Response:
    data = await request.post()
    name = (data.get("name") or "").strip()
    color = (data.get("color") or "").strip()
    parent_id_raw = (data.get("parentCategoryId") or "").strip()

    if not name:
        raise web.HTTPBadRequest(text="Category name is required.")
    if not color:
        raise web.HTTPBadRequest(text="Category color is required.")

    create_category(
        {
            "name": name,
            "nature": _parse_nature(data.get("nature")),
            "color": color,
            "parentCategoryId": int(parent_id_raw) if parent_id_raw else None,
        }
    )
    return_account_id = _parse_optional_account_id((data.get("return_account_id") or "").strip())
    raise web.HTTPFound(_build_redirect_url(return_account_id))


async def update_account_handler(request: web.Request) -> web.Response:
    data = await request.post()
    account_id = int((data.get("id") or "0").strip())
    beginning_balance = float((data.get("beginningBalance") or "0").strip())
    payload = {
        "name": (data.get("name") or "").strip(),
        "description": (data.get("description") or "").strip(),
        "beginningBalance": beginning_balance,
    }
    if not payload["name"]:
        raise web.HTTPBadRequest(text="Account name is required.")
    update_account(account_id, payload)
    return_account_id = _parse_optional_account_id((data.get("return_account_id") or "").strip())
    raise web.HTTPFound(_build_redirect_url(return_account_id))


async def delete_account_handler(request: web.Request) -> web.Response:
    data = await request.post()
    account_id = int((data.get("id") or "0").strip())
    delete_account(account_id)
    return_account_id = _parse_optional_account_id((data.get("return_account_id") or "").strip())
    if return_account_id == account_id:
        return_account_id = None
    raise web.HTTPFound(_build_redirect_url(return_account_id))


async def update_category_handler(request: web.Request) -> web.Response:
    data = await request.post()
    category_id = int((data.get("id") or "0").strip())
    parent_id_raw = (data.get("parentCategoryId") or "").strip()
    payload = {
        "name": (data.get("name") or "").strip(),
        "nature": _parse_nature(data.get("nature")),
        "color": (data.get("color") or "").strip(),
        "parentCategoryId": int(parent_id_raw) if parent_id_raw else None,
    }
    if not payload["name"] or not payload["color"]:
        raise web.HTTPBadRequest(text="Category name and color are required.")
    update_category(category_id, payload)
    return_account_id = _parse_optional_account_id((data.get("return_account_id") or "").strip())
    raise web.HTTPFound(_build_redirect_url(return_account_id))


async def delete_category_handler(request: web.Request) -> web.Response:
    data = await request.post()
    category_id = int((data.get("id") or "0").strip())
    delete_category(category_id)
    return_account_id = _parse_optional_account_id((data.get("return_account_id") or "").strip())
    raise web.HTTPFound(_build_redirect_url(return_account_id))


async def update_record_handler(request: web.Request) -> web.Response:
    data = await request.post()
    return_to = (data.get("return_to") or "").strip()
    record_id = int((data.get("id") or "0").strip())
    account_id = int((data.get("accountId") or "0").strip())
    amount = float((data.get("amount") or "0").strip())
    label = (data.get("label") or "").strip()
    date_raw = (data.get("date") or "").strip()
    if not label:
        raise web.HTTPBadRequest(text="Record label is required.")
    date_value = datetime.fromisoformat(date_raw) if date_raw else datetime.now()
    category_id_raw = (data.get("categoryId") or "").strip()
    payload = {
        "label": label,
        "amount": amount,
        "date": date_value,
        "isIncome": data.get("isIncome") == "on",
        "isTransfer": False,
        "accountId": account_id,
        "categoryId": int(category_id_raw) if category_id_raw else None,
        "transferToAccountId": None,
    }
    update_record(record_id, payload)
    if return_to.startswith("/"):
        raise web.HTTPFound(return_to)
    return_account_id = _parse_optional_account_id((data.get("return_account_id") or "").strip())
    raise web.HTTPFound(_build_redirect_url(return_account_id or account_id))


async def delete_record_handler(request: web.Request) -> web.Response:
    data = await request.post()
    return_to = (data.get("return_to") or "").strip()
    record_id = int((data.get("id") or "0").strip())
    delete_record(record_id)
    if return_to.startswith("/"):
        raise web.HTTPFound(return_to)
    return_account_id = _parse_optional_account_id((data.get("return_account_id") or "").strip())
    raise web.HTTPFound(_build_redirect_url(return_account_id))


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
    app.router.add_get("/accounts/{account_id}/records", account_records_page)
    app.router.add_get("/accounts/{account_id}/records/", account_records_page)
    app.router.add_get("/api/accounts", api_accounts)
    app.router.add_get("/api/categories", api_categories)
    app.router.add_get("/api/records", api_records)
    app.router.add_post("/accounts/create", create_account_handler)
    app.router.add_post("/accounts/update", update_account_handler)
    app.router.add_post("/accounts/delete", delete_account_handler)
    app.router.add_post("/categories/create", create_category_handler)
    app.router.add_post("/categories/update", update_category_handler)
    app.router.add_post("/categories/delete", delete_category_handler)
    app.router.add_post("/records/create", create_record_handler)
    app.router.add_post("/records/update", update_record_handler)
    app.router.add_post("/records/delete", delete_record_handler)
    app.router.add_get("/records/export", export_records_handler)
    app.router.add_get("/reports/categories/export", export_category_report_handler)
    app.router.add_post("/records/import", import_records_handler)
    app.router.add_post("/records/restore", restore_record_handler)

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
