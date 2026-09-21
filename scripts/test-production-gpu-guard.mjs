import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

const source = fs.readFileSync(new URL("../custom_nodes/ComfyUI-AIToolkit-Training/web/production_gpu_guard.js", import.meta.url), "utf8");
let extension;
let gpu = "cuda:0 NVIDIA GeForce RTX 4070";
let online = true;
let posted = 0;
let checked = 0;
let notice;
let forwarded;
const scheduled = [];
const document = {
    getElementById() { return notice; },
    createElement(tag) {
        return { tag, style: {}, children: [], setAttribute() {},
            append(...items) { this.children.push(...items); },
            remove() { notice = undefined; } };
    },
    body: { append(item) { notice = item; } },
};
const api = {
    async fetchApi(path) {
        assert.equal(path, "/system_stats");
        checked++;
        if (!online) throw new Error("offline");
        return { ok: true, async json() { return { devices: [{ name: gpu }] }; } };
    },
    async queuePrompt(...args) {
        assert.equal(this, api);
        posted++;
        forwarded = args;
        return { prompt_id: "accepted" };
    },
};
class PromptExecutionError extends Error {
    constructor(response, status) { super(response.error.details); this.response = response; this.status = status; }
}
const app = { graph: { _nodes: [] }, registerExtension(value) { extension = value; } };
vm.runInNewContext(source.replace(/^import .*;\r?\n/gm, ""), {
    app, api, document, PromptExecutionError, URL, AbortSignal,
    setTimeout(callback) { scheduled.push(callback); },
    window: { location: { href: "http://127.0.0.1:8189/?unrelated=1#old" } },
});
extension.setup();
const names = [
    "Flux2Klein9BMitchIdentityStudioVisualPresetsV11",
    "Flux2Klein9BMitchGroupSceneStudioVisualPresetsV11",
    "Flux2Klein9BPhotoRealismUpgradeV11",
    "Flux2Klein9BGroupLoungeFasterQuality",
    "Flux2Klein9BSpeedUNETLoader",
    "Flux2Klein9BSpeedCLIPLoader",
    "Flux2Klein9BSpeedVAELoader",
    "Flux2Klein9BSpeedSampler",
];
extension.nodeCreated({ type: names[0] });
assert.equal(scheduled.length, 0, "Node registration must not access an uninitialized graph");
for (const name of names) {
    const graph = { output: { 2: { class_type: name, inputs: { seed: 123 } } } };
    const before = JSON.stringify(graph);
    gpu = "cuda:0 NVIDIA GeForce RTX 4070";
    const previousPosts = posted;
    await assert.rejects(api.queuePrompt(0, graph), /port 8188/);
    assert.equal(posted, previousPosts, "Wrong-worker jobs must never be submitted");
    assert.equal(notice.children[1].href, "http://127.0.0.1:8188/");
    assert.equal(notice.children[1].target, "_blank");
    if (name.includes("Speed") || name.includes("GroupLoungeFasterQuality")) {
        assert.match(notice.children[0].textContent, /Mitch\/production-speed/);
    }
    assert.equal(JSON.stringify(graph), before, "Do not alter the locked graph");
    gpu = "cuda:0 NVIDIA GeForce RTX 3090";
    const options = { previewMethod: "none" };
    assert.equal((await api.queuePrompt(-1, graph, options)).prompt_id, "accepted");
    assert.equal(forwarded[0], -1);
    assert.equal(forwarded[1], graph);
    assert.equal(forwarded[2], options);
    assert.equal(notice, undefined);
}
const locked = { output: { 2: { class_type: names[0] } } };
const previousPosts = posted;
online = false;
await assert.rejects(api.queuePrompt(0, locked), /No job was submitted/);
assert.equal(posted, previousPosts);
const previousChecks = checked;
await api.queuePrompt(0, { output: { 1: { class_type: "KSampler" } } });
assert.equal(checked, previousChecks, "Other workflows must remain unaffected");
online = true;
gpu = "cuda:0 NVIDIA GeForce RTX 4070";
app.graph._nodes = [{ type: names[0] }];
await extension.afterConfigureGraph();
assert.match(notice.children[0].textContent, /RTX 4070/);
const addedNode = { type: names[0] };
extension.nodeCreated(addedNode);
assert.equal(scheduled.length, 1);
addedNode.onRemoved();
assert.equal(scheduled.length, 2);
app.graph._nodes = [];
await extension.afterConfigureGraph();
assert.equal(notice, undefined);
console.log("Production GPU guard: existing production and all Speed nodes blocked on 4070, passed through unchanged on 3090; offline, unrelated workflow and graph-switch checks passed.");
