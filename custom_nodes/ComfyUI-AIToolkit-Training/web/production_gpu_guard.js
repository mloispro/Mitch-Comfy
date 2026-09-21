import { app } from "../../scripts/app.js";
import { api, PromptExecutionError } from "../../scripts/api.js";

// The engines enforce this lock too. Catch a wrong-worker tab before submitting
// a job, without rerouting requests, changing inputs, or weakening that lock.
const LOCKED_NODES = new Set([
    "Flux2Klein9BMitchIdentityStudioVisualPresetsV11",
    "Flux2Klein9BMitchGroupSceneStudioVisualPresetsV11",
    "Flux2Klein9BPhotoRealismUpgradeV11",
    "Flux2Klein9BMitchIdentityStudioV1",
    "Flux2Klein9BMitchGroupSceneStudioV1",
    "Flux2Klein9BPhotoRealismUpgradeV1",
    "Flux2Klein9BGroupLoungeFasterQuality",
    "Flux2Klein9BSpeedUNETLoader",
    "Flux2Klein9BSpeedCLIPLoader",
    "Flux2Klein9BSpeedVAELoader",
    "Flux2Klein9BSpeedSampler",
]);
const NOTICE_ID = "mitch-production-gpu-notice";
const PRIMARY_URL = new URL(window.location.href);
PRIMARY_URL.port = "8188";
PRIMARY_URL.pathname = "/";
PRIMARY_URL.search = "";
PRIMARY_URL.hash = "";
let refreshVersion = 0;
let graphReady = false;

function requires3090(nodes) {
    return nodes.some((node) => LOCKED_NODES.has(node.class_type ?? node.type));
}

async function workerName() {
    const response = await api.fetchApi("/system_stats", {
        cache: "no-store",
        signal: AbortSignal.timeout(5000),
    });
    if (!response.ok) throw new Error(`Worker check returned HTTP ${response.status}.`);
    const stats = await response.json();
    const name = stats.devices?.[0]?.name;
    if (!name) throw new Error("Worker did not report its GPU.");
    return name;
}

function showNotice(message) {
    document.getElementById(NOTICE_ID)?.remove();
    if (!message) return;
    const notice = document.createElement("aside");
    notice.id = NOTICE_ID;
    notice.setAttribute("role", "status");
    notice.style.cssText = "position:fixed;bottom:24px;right:24px;z-index:10000;max-width:420px;padding:16px 20px;border:1px solid #e0a33e;border-radius:10px;background:#292319;color:#fff4dc;font:14px/1.5 system-ui;box-shadow:0 4px 20px #0006";
    const text = document.createElement("div");
    text.textContent = message;
    const link = document.createElement("a");
    link.textContent = "Open RTX 3090 ComfyUI (8188)";
    link.href = PRIMARY_URL.href;
    link.target = "_blank";
    link.rel = "noopener";
    link.style.cssText = "display:block;margin-top:8px;color:#ffd084;text-decoration:underline";
    notice.append(text, link);
    document.body.append(notice);
}

function wrongWorkerMessage(name, nodes = []) {
    if (nodes.some((node) => /^(Flux2Klein9BSpeed|Flux2Klein9BGroupLoungeFasterQuality)/.test(node.class_type ?? node.type ?? ""))) {
        return `Production Speed requires the RTX 3090. This tab uses ${name}. Open port 8188, then choose the workflow in Mitch/production-speed.`;
    }
    return `Production Klein 9B workflows require the RTX 3090. This tab uses ${name}. Open port 8188, then choose the workflow in Mitch/production.`;
}

async function refreshNotice() {
    const version = ++refreshVersion;
    if (!requires3090(app.rootGraph?._nodes ?? app.graph?._nodes ?? [])) {
        showNotice(null);
        return;
    }
    let message = null;
    try {
        const name = await workerName();
        if (!name.includes("RTX 3090")) message = wrongWorkerMessage(name, app.rootGraph?._nodes ?? app.graph?._nodes ?? []);
    } catch {
        message = "Cannot verify the GPU for this production Klein 9B workflow. Check that the RTX 3090 worker on port 8188 is online before running.";
    }
    if (version === refreshVersion) showNotice(message);
}

app.registerExtension({
    name: "Mitch.ProductionGpuGuard",
    setup() {
        const originalQueuePrompt = api.queuePrompt;
        api.queuePrompt = async function (number, data, ...args) {
            if (requires3090(Object.values(data.output ?? {}))) {
                let message;
                try {
                    const name = await workerName();
                    if (!name.includes("RTX 3090")) message = wrongWorkerMessage(name, Object.values(data.output ?? {}));
                } catch {
                    message = "Cannot verify the RTX 3090 worker. No job was submitted. Check port 8188 and try again.";
                }
                if (message) {
                    showNotice(message);
                    throw new PromptExecutionError({
                        error: {
                            type: "production_gpu_mismatch",
                            message: "Production Klein 9B requires the RTX 3090",
                            details: message,
                            extra_info: {},
                        },
                        node_errors: {},
                    }, 400);
                }
            }
            showNotice(null);
            return originalQueuePrompt.call(this, number, data, ...args);
        };
    },
    afterConfigureGraph() {
        graphReady = true;
        return refreshNotice();
    },
    nodeCreated(node) {
        // ComfyUI also constructs temporary nodes while registering definitions,
        // before its graph exists. Only inspect a configured graph.
        if (!graphReady || !requires3090([node])) return;
        setTimeout(refreshNotice, 0);
        const removed = node.onRemoved;
        node.onRemoved = function (...args) {
            const result = removed?.apply(this, args);
            setTimeout(refreshNotice, 0);
            return result;
        };
    },
});
