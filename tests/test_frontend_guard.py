"""HTTP integration, no ComfyUI model imports or GPU execution."""
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer
from multidict import CIMultiDict
from h3draft.frontend_guard import (
    ASSET_NAMES, BUILD_HEADER, SESSION_HEADER, MANIFEST_ROUTE, UI_BUILD,
    install_frontend_guard, make_manifest, rejection_reason,
)

PROMPT = {"prompt": {"15": {"class_type": "H3DraftSampler", "inputs": {"preview_steps": 3}}}}


class FrontendGuardHTTPTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.webdir = Path(self.tmp.name) / "test-h3" / "web"
        self.webdir.mkdir(parents=True)
        for name in ASSET_NAMES:
            (self.webdir / name).write_text("// test asset", encoding="utf-8")
        self.server = SimpleNamespace(app=web.Application(), routes=web.RouteTableDef())
        self.handler_calls = 0
        self.last_body = None
        self.assertTrue(install_frontend_guard(self.server, self.webdir))
        self.assertTrue(install_frontend_guard(self.server, self.webdir))
        self.assertEqual(len(self.server.app.middlewares), 1)

        async def queue_handler(request):
            self.handler_calls += 1
            self.last_body = await request.json()
            return web.json_response({"prompt_id": "accepted"})

        self.server.routes.post("/prompt")(queue_handler)
        self.server.routes.post("/api/prompt")(queue_handler)
        async def asset(_request):
            return web.Response(text="// asset")

        self.server.routes.get("/extensions/test-h3/draft.js")(asset)
        self.server.routes.get("/unrelated.js")(asset)
        self.server.app.add_routes(self.server.routes)
        self.client = TestClient(TestServer(self.server.app))
        await self.client.start_server()
        self.manifest = await (await self.client.get(MANIFEST_ROUTE)).json()

    async def asyncTearDown(self):
        await self.client.close()
        self.tmp.cleanup()

    def browser_headers(self, **extra):
        return {"Origin": "http://localhost", "Sec-Fetch-Mode": "cors", **extra}

    async def test_old_live_page_blocked_before_queue(self):
        response = await self.client.post("/prompt", json=PROMPT, headers=self.browser_headers())
        self.assertEqual(response.status, 409)
        payload = await response.json()
        self.assertEqual(payload["error"]["type"], "h3_frontend_reload_required")
        self.assertIn("unsaved", payload["error"]["message"])
        self.assertEqual(self.handler_calls, 0)

    async def test_matching_browser_passes_without_payload_mutation(self):
        headers = self.browser_headers(**{
            BUILD_HEADER: UI_BUILD, SESSION_HEADER: self.manifest["server_session"]})
        response = await self.client.post("/api/prompt", json=PROMPT, headers=headers)
        self.assertEqual(response.status, 200)
        self.assertEqual(self.handler_calls, 1)
        self.assertEqual(self.last_body, PROMPT)

    async def test_wrong_build_or_session_rejected(self):
        for build, session in [("1.1.1", self.manifest["server_session"]), (UI_BUILD, "b"*32)]:
            response = await self.client.post("/prompt", json=PROMPT, headers=self.browser_headers(**{
                BUILD_HEADER: build, SESSION_HEADER: session}))
            self.assertEqual(response.status, 409)
        self.assertEqual(self.handler_calls, 0)

    async def test_external_api_keeps_existing_contract(self):
        response = await self.client.post("/prompt", json=PROMPT)
        self.assertEqual(response.status, 200)
        self.assertEqual(self.last_body, PROMPT)

    async def test_other_workflows_unaffected(self):
        other = {"prompt": {"1": {"class_type": "KSampler", "inputs": {}}}}
        response = await self.client.post("/prompt", json=other, headers=self.browser_headers())
        self.assertEqual(response.status, 200)
        self.assertEqual(self.last_body, other)

    async def test_manifest_is_readonly_nocache_and_assets_scoped(self):
        response = await self.client.get(MANIFEST_ROUTE)
        self.assertIn("no-store", response.headers["Cache-Control"])
        self.assertEqual((await response.json())["ui_build"], UI_BUILD)
        self.assertTrue(self.manifest["assets_available"])
        self.assertEqual(self.handler_calls, 0)
        own = await self.client.get("/extensions/test-h3/draft.js")
        self.assertIn("no-store", own.headers["Cache-Control"])
        other = await self.client.get("/unrelated.js")
        self.assertNotIn("Cache-Control", other.headers)

    async def test_saved_old_widget_metadata_does_not_select_loaded_js(self):
        payload = {**PROMPT, "extra_data": {"extra_pnginfo": {"workflow": {"nodes": [
            {"id": 15, "type": "H3DraftSampler", "properties": {"ver": "1.1.0"}}]}}}}
        response = await self.client.post("/prompt", json=payload, headers=self.browser_headers(**{
            BUILD_HEADER: UI_BUILD, SESSION_HEADER: self.manifest["server_session"]}))
        self.assertEqual(response.status, 200)
        self.assertEqual(self.last_body, payload)


class GuardUnitTests(unittest.TestCase):
    def test_missing_assets_fail_closed_for_browser(self):
        with tempfile.TemporaryDirectory() as d:
            manifest = make_manifest(d, "a"*32)
        self.assertFalse(manifest["assets_available"])
        headers = CIMultiDict({"origin": "http://localhost", BUILD_HEADER: UI_BUILD, SESSION_HEADER: "a"*32})
        self.assertEqual(rejection_reason(headers, PROMPT, manifest), "incomplete_frontend_install")

    def test_old_legacy_node_request_is_guarded(self):
        manifest = {"ui_build": UI_BUILD, "server_session": "a"*32, "assets_available": True}
        for node_type in ("H3T2VADraft", "H3T2VAContinue", "H3ContinueSampler"):
            payload = {"prompt": {"1": {"class_type": node_type}}}
            self.assertEqual(rejection_reason(CIMultiDict({"Sec-Fetch-Mode": "cors"}), payload, manifest), "ui_build_mismatch")


if __name__ == "__main__":
    unittest.main()
