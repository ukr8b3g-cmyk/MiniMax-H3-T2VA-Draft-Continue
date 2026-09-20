export const LIFECYCLE_BRIDGE_MARK = Symbol.for("MiniMax.H3.DraftContinue.loadGraphDataLifecycleBridge");

export function installLoadGraphDataLifecycleBridge(app, hooks = {}) {
  if (!app || typeof app.loadGraphData !== "function") {
    return { installed: false, reason: "loadGraphData unavailable" };
  }

  const current = app.loadGraphData;
  if (current[LIFECYCLE_BRIDGE_MARK]) {
    return { installed: false, alreadyInstalled: true };
  }

  const original = current;
  async function wrappedLoadGraphData(...args) {
    let context;
    try {
      context = hooks.before?.(args);
    } catch (error) {
      hooks.onBridgeError?.("before", error);
    }

    let result;
    try {
      result = await original.apply(this, args);
    } catch (error) {
      try {
        hooks.onLoadError?.(error, args, context);
      } catch (bridgeError) {
        hooks.onBridgeError?.("load_error", bridgeError);
      }
      throw error;
    }

    try {
      await hooks.after?.(result, args, context);
    } catch (error) {
      hooks.onBridgeError?.("after", error);
    }
    return result;
  }

  Object.defineProperty(wrappedLoadGraphData, LIFECYCLE_BRIDGE_MARK, {
    value: true,
    enumerable: false,
    configurable: false,
  });
  Object.defineProperty(wrappedLoadGraphData, "__h3DraftOriginalLoadGraphData", {
    value: original,
    enumerable: false,
    configurable: false,
  });

  app.loadGraphData = wrappedLoadGraphData;
  return { installed: true };
}
