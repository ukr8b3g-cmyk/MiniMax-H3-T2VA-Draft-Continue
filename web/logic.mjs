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
