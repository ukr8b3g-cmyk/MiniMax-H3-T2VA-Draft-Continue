import test from "node:test";
import assert from "node:assert/strict";
import { installLoadGraphDataLifecycleBridge } from "../web/lifecycle.mjs";

test("lifecycle bridge captures before and restores after loadGraphData", async () => {
  const order = [];
  const app = {
    value: 0,
    async loadGraphData(next, clean = true) {
      order.push(["load", this === app, next, clean]);
      this.value = next;
      return "loaded";
    },
  };
  const installed = installLoadGraphDataLifecycleBridge(app, {
    before(args) {
      order.push(["before", ...args]);
      return { previous: app.value };
    },
    after(result, args, context) {
      order.push(["after", result, args[0], context.previous, app.value]);
    },
  });

  assert.equal(installed.installed, true);
  const result = await app.loadGraphData(7, true);
  assert.equal(result, "loaded");
  assert.deepEqual(order, [
    ["before", 7, true],
    ["load", true, 7, true],
    ["after", "loaded", 7, 0, 7],
  ]);
});

test("lifecycle bridge is idempotent", () => {
  const app = { async loadGraphData() { return true; } };
  const first = installLoadGraphDataLifecycleBridge(app);
  const wrapped = app.loadGraphData;
  const second = installLoadGraphDataLifecycleBridge(app);
  assert.equal(first.installed, true);
  assert.equal(second.alreadyInstalled, true);
  assert.equal(app.loadGraphData, wrapped);
});

test("lifecycle bridge rethrows load errors and does not run after", async () => {
  const calls = [];
  const expected = new Error("load failed");
  const app = {
    async loadGraphData() {
      throw expected;
    },
  };
  installLoadGraphDataLifecycleBridge(app, {
    before() { calls.push("before"); return "ctx"; },
    after() { calls.push("after"); },
    onLoadError(error, _args, context) {
      calls.push(["load-error", error, context]);
    },
  });

  await assert.rejects(app.loadGraphData(), error => error === expected);
  assert.deepEqual(calls, ["before", ["load-error", expected, "ctx"]]);
});

test("bridge hook failure never blocks core load", async () => {
  const errors = [];
  const app = { async loadGraphData() { return 42; } };
  installLoadGraphDataLifecycleBridge(app, {
    before() { throw new Error("before hook"); },
    after() { throw new Error("after hook"); },
    onBridgeError(stage, error) { errors.push([stage, error.message]); },
  });
  assert.equal(await app.loadGraphData(), 42);
  assert.deepEqual(errors, [["before", "before hook"], ["after", "after hook"]]);
});
