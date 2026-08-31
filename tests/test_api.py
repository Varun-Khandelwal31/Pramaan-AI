import unittest
import io
import zipfile
import asyncio
import httpx
from backend.app import app
from backend.database import seed

class TestPramaanAPI(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        seed.seed_database(force=True)
        self.transport = httpx.ASGITransport(app=app)
        self.client = httpx.AsyncClient(transport=self.transport, base_url="http://testserver")

    async def asyncTearDown(self):
        await self.client.aclose()

    async def test_system_health_endpoint(self):
        res = await self.client.get("/api/system/health")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "online")
        self.assertGreaterEqual(data["total_cases"], 7)

    async def test_role_switch_endpoint(self):
        res = await self.client.post("/api/set-role", json={"role": "Court"})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["role"], "Court")

    async def test_dossier_zip_export(self):
        # Reset role to Hospital
        await self.client.post("/api/set-role", json={"role": "Hospital"})
        res = await self.client.get("/cases/1/export-bundle")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.headers["content-type"], "application/zip")

        z = zipfile.ZipFile(io.BytesIO(res.content))
        names = z.namelist()
        self.assertIn("README_COURT_INSTRUCTIONS.txt", names)
        self.assertIn("Section_63_BSA_Certificate.html", names)
        self.assertIn("Evidence_Chain_Manifest.txt", names)
        self.assertIn("Cryptographic_Audit_Trail.json", names)

    async def test_iot_telemetry_breach_simulation(self):
        res = await self.client.post("/api/telemetry/simulate-breach", json={
            "sensor_id": "M-04",
            "temperature": 8.5,
            "reason": "Test Power Outage",
            "case_id": 1
        })
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data["is_breached"])
        self.assertIn("breach_hash", data)

    async def test_merkle_proof_endpoint(self):
        res = await self.client.get("/api/anchor/merkle-proof/1")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("proof", data)
        self.assertTrue(data["proof"]["is_valid"])

    async def test_all_web_routes(self):
        await self.client.post("/api/set-role", json={"role": "Hospital"})
        routes = [
            "/",
            "/dashboard",
            "/cases/new",
            "/cases/1",
            "/records/1",
            "/verify/1",
            "/certificate/1",
            "/anchor",
            "/integrations",
            "/telemetry"
        ]
        for route in routes:
            res = await self.client.get(route)
            self.assertEqual(res.status_code, 200, f"Route {route} failed with {res.status_code}")

if __name__ == "__main__":
    unittest.main()
