"""Browser build handshake; no model, sampler, tensor or workflow mutations.

This is a stale-client guard, NOT authentication. Non-browser API clients keep
using the existing API contract. Browser requests are identified by Fetch
Metadata/Origin headers and checked before ComfyUI's /prompt handler.
"""
from __future__ import annotations

import hashlib
import logging
from pathlib import Path
import uuid

UI_BUILD = "1.7.5"
PROTOCOL = 1
BUILD_HEADER = "X-H3-Draft-UI"
SESSION_HEADER = "X-H3-Draft-Session"
MANIFEST_ROUTE = "/h3draft/ui-build"
NODE_TYPES = frozenset({"H3T2VADraft", "H3T2VAContinue", "H3DraftSampler", "H3ContinueSampler"})
ASSET_NAMES = ("draft.js", "logic.mjs", "lifecycle.mjs", "frontend_guard.mjs")
_RELOAD_MESSAGE = (
    "H3 Draft frontend is outdated or unverified. Protect/export every unsaved "
    "workflow, then fully reload this browser page and generate a new Preview. "
    "Restarting ComfyUI alone does not update an already-open page. "
    "未保存Workflowを保護してからページを完全再読込してください。"
)


def has_review_nodes(payload):
    prompt = payload.get("prompt") if isinstance(payload, dict) else None
    return isinstance(prompt, dict) and any(
        isinstance(node, dict) and node.get("class_type") in NODE_TYPES
        for node in prompt.values()
    )


def make_manifest(web_dir, session_id=None):
    """Hashes describe installed files, not JavaScript already executing in a tab."""
    root = Path(web_dir)
    assets = {}
    for name in ASSET_NAMES:
        try:
            assets[name] = hashlib.sha256((root / name).read_bytes()).hexdigest()
        except OSError:
            assets[name] = None
    return {
        "protocol": PROTOCOL,
        "ui_build": UI_BUILD,
        "server_session": session_id or uuid.uuid4().hex,
        "installed_assets_sha256": assets,
        "assets_available": all(assets.values()),
        "hash_scope": "installed_files_not_executing_browser_memory",
    }


def rejection_reason(headers, payload, manifest):
    if not has_review_nodes(payload):
        return None
    # The caller must supply a case-insensitive HTTP header mapping.
    browser = bool(headers.get("Sec-Fetch-Mode") or headers.get("Origin"))
    declared = headers.get(BUILD_HEADER) or headers.get(SESSION_HEADER)
    if not browser and not declared:
        return None  # Existing scripts, API workflows and direct node execution.
    if headers.get(BUILD_HEADER) != manifest["ui_build"]:
        return "ui_build_mismatch"
    if headers.get(SESSION_HEADER) != manifest["server_session"]:
        return "server_session_mismatch"
    if not manifest["assets_available"]:
        return "incomplete_frontend_install"
    return None


def install_frontend_guard(server=None, web_dir=None):
    """Called once at custom-node import, before aiohttp freezes its middleware."""
    if server is None:
        try:
            from server import PromptServer
        except ImportError:
            return False  # Offline import/tests, not a live ComfyUI server.
        server = getattr(PromptServer, "instance", None)
    if server is None:
        return False
    if getattr(server, "_h3draft_frontend_guard", None) is not None:
        return True

    from aiohttp import web  # Provided by ComfyUI; no new dependency.

    web_dir = Path(web_dir) if web_dir else Path(__file__).resolve().parents[1] / "web"
    manifest = make_manifest(web_dir)
    extension_prefix = "/extensions/" + web_dir.parent.name + "/"

    @web.middleware
    async def guard(request, handler):
        if request.method == "POST" and request.path in ("/prompt", "/api/prompt"):
            try:
                payload = await request.json()
            except (ValueError, UnicodeError):
                return await handler(request)  # Preserve Core's invalid-body behavior.
            reason = rejection_reason(request.headers, payload, manifest)
            if reason:
                return web.json_response({
                    "error": {
                        "type": "h3_frontend_reload_required",
                        "message": _RELOAD_MESSAGE,
                        "details": "Request was rejected before Queue: " + reason,
                        "extra_info": {"expected_ui_build": UI_BUILD, "reason": reason},
                    },
                    "node_errors": {},
                }, status=409, headers={"Cache-Control": "no-store"})
        response = await handler(request)
        # This prevents future HTTP-cache reuse; it cannot replace an already
        # evaluated JS module. Full page reload remains an explicit user action.
        path = request.path.removeprefix("/api")
        if path.startswith(extension_prefix) and path.rsplit("/", 1)[-1] in ASSET_NAMES:
            response.headers["Cache-Control"] = "no-store, max-age=0"
        return response

    async def ui_build(_request):
        return web.json_response(manifest, headers={"Cache-Control": "no-store, max-age=0"})

    server.app.middlewares.append(guard)
    server.routes.get(MANIFEST_ROUTE)(ui_build)
    server._h3draft_frontend_guard = manifest
    logging.info("[H3 Draft Continue] Browser build guard enabled: %s", UI_BUILD)
    return True
