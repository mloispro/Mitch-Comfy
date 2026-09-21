import { app } from "../../scripts/app.js";

// Keep the backend/API field name and widget position stable. Old boolean
// workflows deserialize to Low/Off, never to a truthy string "off".
function migrate(node) {
    const widget = node.widgets?.find((item) => item.name === "appearance_polish");
    if (!widget) return;
    if (widget.value === true) widget.value = "low";
    if (widget.value === false) widget.value = "off";
    widget.label = "Attractiveness";
}

app.registerExtension({
    name: "Mitch.UpgradeAttractivenessLevels",
    beforeRegisterNodeDef(nodeType, nodeData) {
        if (!["Flux2Klein9BPhotoRealismUpgradeV11", "Flux2Klein9BPhotoRealismUpgradeV1"].includes(nodeData.name)) return;
        const created = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function (...args) {
            const result = created?.apply(this, args);
            migrate(this);
            return result;
        };
        const configured = nodeType.prototype.onConfigure;
        nodeType.prototype.onConfigure = function (...args) {
            const result = configured?.apply(this, args);
            migrate(this);
            return result;
        };
    },
});
