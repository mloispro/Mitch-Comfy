import { app } from "../../scripts/app.js";
import { ComfyWidgets } from "../../scripts/widgets.js";

const POLL_MS = 5000;

function statusText(data) {
    if (!data.found) {
        return data.error || data.message || "No training job found.";
    }
    const lines = [`${data.status.toUpperCase()}  •  ${data.name}`];
    if (data.phase === "downloading_model") {
        lines.push(data.info);
        lines.push("Training starts automatically when the model is ready.");
    } else {
        lines.push(`Step ${Number(data.step).toLocaleString()} / ${Number(data.total_steps).toLocaleString()}  (${data.progress_percent}%)`);
        if (data.info) lines.push(data.info);
        if (data.speed) lines.push(`Speed: ${data.speed}${data.eta ? `  •  ETA: ${data.eta}` : ""}`);
    }
    if (data.publish_note) lines.push(data.publish_note);
    if (data.lora_name) lines.push(`LoRA: ${data.lora_name}`);
    lines.push(`Updated: ${new Date().toLocaleTimeString()}`);
    return lines.join("\n");
}

app.registerExtension({
    name: "AIToolkit.LiveGeneratedDatasetStatus",
    async beforeRegisterNodeDef(nodeType, nodeData, appRef) {
        if (nodeData.name !== "AIToolkitTrainGeneratedDataset") return;

        const originalCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function () {
            originalCreated?.apply(this, arguments);
            const node = this;
            const widget = ComfyWidgets["STRING"](
                node,
                "Live training progress",
                ["STRING", { multiline: true, default: "Checking AI-Toolkit…" }],
                appRef,
            ).widget;
            widget.serializeValue = async () => "";
            widget.disabled = true;
            if (widget.inputEl) widget.inputEl.readOnly = true;
            node.setSize([Math.max(node.size[0], 470), Math.max(node.size[1], 310)]);

            const update = async () => {
                if (document.hidden || node.__aitkStatusBusy) return;
                node.__aitkStatusBusy = true;
                try {
                    const response = await fetch("/aitk/generated-dataset/status", {
                        method: "POST",
                        cache: "no-store",
                        headers: { "Content-Type": "application/json" },
                        body: "{}",
                    });
                    const data = await response.json();
                    widget.value = statusText(data);
                    widget.inputEl?.dispatchEvent(new Event("input"));
                } catch (error) {
                    widget.value = `Live status unavailable\n${error.message}\nRetrying automatically…`;
                } finally {
                    node.__aitkStatusBusy = false;
                    appRef.graph.setDirtyCanvas(true, true);
                }
            };

            node.__aitkStatusTimer = window.setInterval(update, POLL_MS);
            node.__aitkVisibilityHandler = () => { if (!document.hidden) update(); };
            document.addEventListener("visibilitychange", node.__aitkVisibilityHandler);
            update();
        };

        const originalRemoved = nodeType.prototype.onRemoved;
        nodeType.prototype.onRemoved = function () {
            if (this.__aitkStatusTimer) window.clearInterval(this.__aitkStatusTimer);
            if (this.__aitkVisibilityHandler) {
                document.removeEventListener("visibilitychange", this.__aitkVisibilityHandler);
            }
            originalRemoved?.apply(this, arguments);
        };
    },
});
