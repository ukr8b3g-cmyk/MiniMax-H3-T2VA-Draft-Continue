/** Stale-page protection. No automatic reload, persistent storage or workflow edits. */
export const UI_BUILD = "1.7.5";
const INSTALL = Symbol.for("MiniMax.H3.DraftContinue.frontendGuard");
const BRIDGE = Symbol.for("MiniMax.H3.DraftContinue.loadGraphDataLifecycleBridge");
const REVIEW = new Set(["H3T2VADraft", "H3T2VAContinue", "H3DraftSampler", "H3ContinueSampler"]);
export const RELOAD_HELP = "Protect/export unsaved workflows, fully reload this page, then generate a new Preview. No automatic reload is performed.";

export function isReviewRequest(route, options) {
  if (typeof route !== "string" || !/^\/(?:api\/)?prompt(?:\?|$)/.test(route) ||
      String(options?.method ?? "GET").toUpperCase() !== "POST" || typeof options?.body !== "string") return false;
  try {
    const prompt = JSON.parse(options.body)?.prompt;
    return prompt && typeof prompt === "object" && !Array.isArray(prompt) &&
      Object.values(prompt).some(node => REVIEW.has(node?.class_type));
  } catch { return false; }
}

export function installFrontendGuard({api, app, runtime, onChange = () => {}}) {
  if (api[INSTALL]) return api[INSTALL];
  const original = api.fetchApi;
  if (typeof original !== "function") throw new Error("H3 frontend guard needs ComfyUI api.fetchApi.");
  let state = {status: "checking", loadedBuild: UI_BUILD, serverBuild: null, message: "Checking loaded UI against backend…"};
  let knownSession = null;
  let flight = null;
  let reloadRequired = false;
  const listeners = new Set([onChange]);
  function publish(next) {
    state = {...state, ...next};
    runtime.frontendGuard = {...state};
    for (const listener of listeners) listener({...state});
    return state;
  }
  function block(message, status = "reload_required") {
    if (status === "reload_required") reloadRequired = true;
    publish({status, message: message + " " + RELOAD_HELP});
    throw new Error(state.message);
  }
  async function check() {
    if (reloadRequired) throw new Error(state.message);
    if (runtime.loaded !== true || runtime.version !== UI_BUILD || runtime.logicStateContract !== "native" ||
        !String(runtime.lifecycleBridge).startsWith("loadGraphData-wrapper") || !app.loadGraphData?.[BRIDGE]) {
      return block("The current page did not load the expected H3 UI and lifecycle bridge.");
    }
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 5000);
    let manifest;
    try {
      const response = await original.call(api, "/h3draft/ui-build", {
        method: "GET", cache: "no-store", signal: controller.signal,
      });
      if (!response.ok) throw new Error(`UI manifest HTTP ${response.status}`);
      manifest = await response.json();
    } catch (error) {
      return block(`Cannot verify backend UI build: ${error.message}.`, "offline");
    } finally { clearTimeout(timer); }
    if (manifest?.protocol !== 1 || manifest.ui_build !== UI_BUILD || manifest.assets_available !== true ||
        !/^[a-f0-9]{32}$/.test(manifest.server_session ?? "")) {
      publish({serverBuild: manifest?.ui_build ?? null});
      return block("Loaded UI and installed backend build do not match.");
    }
    if (knownSession !== null && knownSession !== manifest.server_session) {
      return block("ComfyUI restarted. Old Preview approvals cannot be reused.");
    }
    knownSession = manifest.server_session;
    return publish({status: "verified", serverBuild: manifest.ui_build, serverSession: knownSession,
      installedAssets: manifest.installed_assets_sha256,
      message: `UI ${UI_BUILD} / backend ${manifest.ui_build} verified · lifecycle bridge active`});
  }
  function verify() {
    if (!flight) flight = check().finally(() => { flight = null; });
    return flight;
  }
  const guard = {
    verify,
    get state() { return {...state}; },
    subscribe(listener) { listeners.add(listener); listener({...state}); return () => listeners.delete(listener); },
  };
  // Intercept only H3 review POSTs, including the standard Run button. Preserve
  // request body, this-binding, options, headers and any future extra arguments.
  api.fetchApi = async function(route, options, ...rest) {
    if (!isReviewRequest(route, options)) return original.call(this, route, options, ...rest);
    const checked = await verify();
    const headers = new Headers(options.headers);
    headers.set("X-H3-Draft-UI", UI_BUILD);
    headers.set("X-H3-Draft-Session", checked.serverSession);
    const response = await original.call(this, route, {...options, headers}, ...rest);
    if (response.status === 409) {
      const body = await response.clone().json().catch(() => null);
      if (body?.error?.type === "h3_frontend_reload_required") {
        reloadRequired = true;
        publish({status: "reload_required", message: body.error.message});
      }
    }
    return response;
  };
  Object.defineProperty(api, INSTALL, {value: guard});
  api.addEventListener?.("reconnected", () => { void verify().catch(() => {}); });
  publish(state);
  return guard;
}
