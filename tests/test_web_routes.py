import asyncio
from io import BytesIO
from pathlib import Path

from aiohttp import FormData
from aiohttp.test_utils import TestClient, TestServer

from bagels.web import create_app


def test_export_records_route(tmp_path: Path):
    async def run():
        app = create_app(tmp_path)
        server = TestServer(app)
        client = TestClient(server)
        await client.start_server()
        try:
            await client.post(
                "/accounts/create",
                data={"name": "Export Account", "description": "", "beginningBalance": "100"},
                allow_redirects=False,
            )
            response = await client.get("/api/accounts")
            data = await response.json()
            account_id = next(
                (acc["id"] for acc in data["accounts"] if acc["name"] == "Export Account"),
                None,
            )
            assert account_id is not None

            await client.post(
                "/records/create",
                data={
                    "label": "Test Export",
                    "amount": "12.50",
                    "date": "2026-05-10",
                    "accountId": str(account_id),
                },
                allow_redirects=False,
            )

            export_resp = await client.get("/records/export")
            text = await export_resp.text()
            assert "Test Export" in text
            assert "12.5" in text or "12.50" in text
        finally:
            await client.close()
            await server.close()

    asyncio.run(run())


def test_import_records_route(tmp_path: Path):
    async def run():
        app = create_app(tmp_path)
        server = TestServer(app)
        client = TestClient(server)
        await client.start_server()
        try:
            await client.post(
                "/accounts/create",
                data={"name": "Import Account", "description": "", "beginningBalance": "100"},
                allow_redirects=False,
            )
            response = await client.get("/api/accounts")
            data = await response.json()
            account_id = next(
                (acc["id"] for acc in data["accounts"] if acc["name"] == "Import Account"),
                None,
            )
            assert account_id is not None

            csv_bytes = BytesIO(
                b"date,label,amount,account,category,isIncome\n2026-05-10,Imported Item,35.00,Import Account,,0\n"
            )
            form = FormData()
            form.add_field("records_csv", csv_bytes, filename="records.csv", content_type="text/csv")
            import_resp = await client.post("/records/import", data=form, allow_redirects=False)
            assert import_resp.status in (302, 303)

            export_resp = await client.get("/records/export")
            text = await export_resp.text()
            assert "Imported Item" in text
        finally:
            await client.close()
            await server.close()

    asyncio.run(run())
