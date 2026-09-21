import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";

let extension;
const source = fs.readFileSync(new URL("../custom_nodes/ComfyUI-AIToolkit-Training/web/upgrade_attractiveness.js", import.meta.url), "utf8");
vm.runInNewContext(source.replace(/^import .*;\r?\n/, ""), {
    app: { registerExtension(value) { extension = value; } },
});
class Node {
    onNodeCreated() { this.created = true; return 23; }
    onConfigure() { this.configured = true; return 42; }
}
extension.beforeRegisterNodeDef(Node, { name: "Flux2Klein9BPhotoRealismUpgradeV11" });
for (const [input, expected] of [[true, "low"], [false, "off"], ["high", "high"], ["off", "off"]]) {
    const node = new Node();
    node.widgets = [{ name: "appearance_polish", value: input }, { name: "phone_camera_style", value: true }];
    assert.equal(node.onNodeCreated(), 23);
    assert.equal(node.onConfigure(), 42);
    assert.equal(node.widgets[0].value, expected);
    assert.equal(node.widgets[0].label, "Attractiveness");
    assert.equal(node.widgets[1].value, true);
}
class Other {}
extension.beforeRegisterNodeDef(Other, { name: "UnrelatedNode" });
assert.equal(Other.prototype.onConfigure, undefined);
console.log("Upgrade attractiveness UI migration: passed");
