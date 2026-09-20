/** Pure workflow logic, also run by node:test. No global graph mutations. */
export function canonical(value) {
  if (typeof value === "number") {
    if (!Number.isFinite(value)) throw new Error("Non-finite number in fingerprint.");
    const bytes = new Uint8Array(8);
    new DataView(bytes.buffer).setFloat64(0, value === 0 ? 0 : value, false);
    return "n:" + Array.from(bytes, b => b.toString(16).padStart(2, "0")).join("");
  }
  if (Array.isArray(value)) return `[${value.map(canonical).join(",")}]`;
  if (value && typeof value === "object") {
    return `{${Object.keys(value).sort().map(k => `${JSON.stringify(k)}:${canonical(value[k])}`).join(",")}}`;
  }
  return JSON.stringify(value);
}
export function branch(output, roots) {
  const result = {}, active = new Set();
  const visit = id => {
    id = String(id);
    if (active.has(id)) throw new Error("Workflow dependency cycle.");
    if (result[id]) return;
    const node = output[id];
    if (!node?.class_type) throw new Error(`Missing upstream node ${id}.`);
    active.add(id);
    for (const v of Object.values(node.inputs ?? {})) {
      if (Array.isArray(v) && v.length === 2 && typeof v[0] === "string" && output[v[0]] && Number.isInteger(v[1])) visit(v[0]);
    }
    result[id] = { class_type: node.class_type, inputs: node.inputs ?? {} };
    active.delete(id);
  };
  roots.forEach(visit); return result;
}
export async function signature(output, root, cryptoApi = globalThis.crypto) {
  if (!cryptoApi?.subtle) throw new Error("Secure browser context required (localhost / HTTPS).");
  const bytes = new TextEncoder().encode(canonical(branch(output, [String(root)])));
  const hash = await cryptoApi.subtle.digest("SHA-256", bytes);
  return Array.from(new Uint8Array(hash), b => b.toString(16).padStart(2, "0")).join("");
}
export const DRAFT_CLASSES = new Set(["H3T2VADraft", "H3DraftSampler"]);
export const CONTINUE_CLASSES = new Set(["H3T2VAContinue", "H3ContinueSampler"]);
const DEFAULT_OUTPUTS = new Set(["SaveVideo", "SaveImage", "PreviewImage", "SaveAnimatedWEBP",
  "SaveAnimatedPNG", "PreviewAny", "SaveAudio", "SaveAudioMP3", "SaveAudioOpus", "PreviewAudio"]);
export function downstreamOutputs(output, continueId, outputTypes = DEFAULT_OUTPUTS) {
  const root = String(continueId), reached = new Set([root]), todo = [root], sinks = [];
  while (todo.length) {
    const parent = todo.pop();
    for (const [id,n] of Object.entries(output)) {
      if (reached.has(id) || DRAFT_CLASSES.has(n.class_type) || CONTINUE_CLASSES.has(n.class_type)) continue;
      if (!Object.values(n.inputs ?? {}).some(v => Array.isArray(v) && v.length===2 && v[0]===parent && Number.isInteger(v[1]))) continue;
      reached.add(id); todo.push(id); if (outputTypes.has(n.class_type)) sinks.push(id);
    }
  }
  const acceptedAncestors = new Set(Object.keys(branch(output,[root])));
  for (const id of sinks) for (const [a,node] of Object.entries(branch(output,[id]))) {
    if ((DRAFT_CLASSES.has(node.class_type)||CONTINUE_CLASSES.has(node.class_type)) && !acceptedAncestors.has(a))
      throw new Error("A downstream output also needs another Draft/Continue. Separate the review branches before GO.");
  }
  return sinks;
}
export function continueRequest(output, continueId, approvedId, outputTypes=DEFAULT_OUTPUTS) {
  const id=String(continueId);
  if (!CONTINUE_CLASSES.has(output[id]?.class_type) || !/^[a-f0-9]{32}$/.test(approvedId))
    throw new Error("No reviewed Draft State. Generate Preview first.");
  const saves=downstreamOutputs(output,id,outputTypes);
  const copy=JSON.parse(JSON.stringify(branch(output,[id,...saves])));
  copy[id].inputs.go=true; copy[id].inputs.approved_state_id=approvedId; return copy;
}
export function safeWorkflow(workflow) {
  const copy=JSON.parse(JSON.stringify(workflow));
  function reset(nodes){ for(const n of nodes??[]){ if(!CONTINUE_CLASSES.has(n.type)) continue;
    if(Array.isArray(n.widgets_values)){n.widgets_values[0]=false;n.widgets_values[1]="";}
    if(n.widgets_values_named){n.widgets_values_named.go=false;n.widgets_values_named.approved_state_id="";}}}
  reset(copy.nodes); for(const s of copy.definitions?.subgraphs??[]) reset(s.nodes); return copy;
}
export function newSeed(cryptoApi=globalThis.crypto){const v=new Uint32Array(2);cryptoApi.getRandomValues(v);return (v[0]&0x1fffff)*4294967296+v[1];}
export function externalSeedTarget(output,draftId){const input=output[String(draftId)]?.inputs?.noise;
  if(!Array.isArray(input)||output[input[0]]?.class_type!=="RandomNoise") return null; return {nodeId:input[0],name:"noise_seed"};}


export const REVIEW_PHASES = new Set([
  "preview_required", "preview_queued", "ready", "stale",
  "continue_queued", "complete", "error",
]);

function finiteNumber(value) {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

export function reviewUiState(input = {}) {
  const phase = REVIEW_PHASES.has(input.phase) ? input.phase : "preview_required";
  const currentStep = Number.isInteger(input.currentStep) && input.currentStep >= 0 ? input.currentStep : 0;
  const totalSteps = Number.isInteger(input.totalSteps) && input.totalSteps >= currentStep ? input.totalSteps : 0;
  const remaining = Math.max(0, totalSteps - currentStep);
  const width = Number.isInteger(input.width) && input.width > 0 ? input.width : null;
  const height = Number.isInteger(input.height) && input.height > 0 ? input.height : null;
  const frameCount = Number.isInteger(input.frameCount) && input.frameCount > 0 ? input.frameCount : null;
  const wall = finiteNumber(input.wallSeconds);
  const message = typeof input.message === "string" ? input.message.trim() : "";

  const geometry = width && height ? `${width}×${height}` : "";
  const frames = frameCount ? `${frameCount}f` : "";
  const wallText = wall !== null ? `Preview ${wall.toFixed(1)}s` : "";
  const previewMeta = [geometry, frames, wallText, "Frame 0 preview · estimate"].filter(Boolean).join(" · ");

  const base = {
    state: phase,
    kind: "idle",
    draft: { title: "PREVIEW REQUIRED", detail: "Review Frame 0 before GO." },
    continue: { title: "WAITING FOR PREVIEW", detail: "Generate and review a Preview first." },
    canPreview: true,
    canReroll: true,
    canGo: false,
  };

  if (phase === "preview_queued") {
    return {
      ...base, kind: "busy", canPreview: false, canReroll: false,
      draft: { title: "PREVIEW RUNNING", detail: "Generating Frame 0 from the full-length H3 latent." },
      continue: { title: "WAITING", detail: "GO unlocks after Preview completes." },
    };
  }
  if (phase === "ready") {
    return {
      ...base, kind: "ready", canGo: true,
      draft: {
        title: totalSteps ? `READY · ${currentStep}/${totalSteps}` : "READY",
        detail: previewMeta || "Frame 0 preview · estimate",
      },
      continue: {
        title: "READY TO GO",
        detail: totalSteps ? `${remaining} sampling steps remaining` : "Continue the reviewed Draft State",
      },
    };
  }
  if (phase === "stale") {
    return {
      ...base, kind: "warning",
      draft: { title: "PREVIEW STALE", detail: message || "Settings changed after Preview." },
      continue: { title: "NEW PREVIEW REQUIRED", detail: "GO is locked until Preview is regenerated." },
    };
  }
  if (phase === "continue_queued") {
    return {
      ...base, kind: "busy", canPreview: false, canReroll: false,
      draft: { title: "REVIEWED", detail: "The approved Draft State is continuing." },
      continue: {
        title: "CONTINUING",
        detail: totalSteps ? `Resume ${currentStep}/${totalSteps} · ${remaining} steps remaining` : "Continuing reviewed state",
      },
    };
  }
  if (phase === "complete") {
    return {
      ...base, kind: "ready",
      draft: { title: "REVIEWED", detail: "Preview/approval cycle completed. Generate a new Preview for another run." },
      continue: { title: "COMPLETE", detail: message || "Reviewed Draft State completed." },
    };
  }
  if (phase === "error") {
    return {
      ...base, kind: "error",
      draft: { title: "REVIEW ERROR", detail: message || "Preview/Continue failed. Generate a new Preview." },
      continue: { title: "NOT READY", detail: "Generate a new Preview before GO." },
    };
  }
  return base;
}
