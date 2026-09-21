import assert from "node:assert/strict";
import fs from "node:fs";
import vm from "node:vm";
import { webcrypto } from "node:crypto";

const scriptUrl = new URL("../custom_nodes/ComfyUI-AIToolkit-Training/web/visual_scene_presets.js", import.meta.url);
const bytes = fs.readFileSync(new URL("./assets/scene-presets/manifest.json", scriptUrl));
const manifest = JSON.parse(bytes);
const hash = Buffer.from(await webcrypto.subtle.digest("SHA-256", bytes)).toString("hex").toUpperCase();
let extension;
const timers = [];
class Element {
  constructor(tag) { this.tagName = tag.toUpperCase(); this.children = []; this.attributes = {}; this.events = {}; }
  append(...items) { this.children.push(...items); }
  appendChild(item) { this.append(item); }
  setAttribute(key, value) { this.attributes[key] = value; }
  addEventListener(key, callback) { this.events[key] = callback; }
  classList = { toggle() {} };
}
const document = { getElementById() {}, createElement: (tag) => new Element(tag), head: new Element("head") };
vm.runInNewContext(fs.readFileSync(scriptUrl, "utf8").replaceAll("import.meta.url", JSON.stringify(scriptUrl.href)), {
  window: { comfyAPI: { app: { app: { registerExtension(value) { extension = value; } } } } },
  document, URL, TextDecoder, Uint8Array, crypto: webcrypto,
  fetch: async () => ({ ok: true, arrayBuffer: async () => bytes }),
  setTimeout(callback) { timers.push(callback); },
});
function flush() { while (timers.length) timers.shift()(); }
const plain = (value) => JSON.parse(JSON.stringify(value));

for (const kind of ["identity", "group"]) {
  const isIdentity = kind === "identity";
  const type = isIdentity ? "Flux2Klein9BMitchIdentityStudioVisualPresetsV11" : "Flux2Klein9BMitchGroupSceneStudioVisualPresetsV11";
  const names = isIdentity
    ? ["reference_profile", "scene_prompt", "appearance_polish", "fast_turbo", "seed", "control_after_generate", "scene_preset"]
    : ["scene_prompt", "target_x", "target_y", "head_scale", "appearance_polish", "fast_turbo", "seed", "control_after_generate", "scene_preset"];
  const workflow = JSON.parse(fs.readFileSync(new URL(`../workflows/production/FLUX.2 Klein 9B Mitch ${isIdentity ? "Identity" : "Group Scene"} Studio v1.1 - Visual Presets.json`, import.meta.url)));
  const original = workflow.nodes.find((node) => node.type === type).widgets_values;
  assert.equal(original.length, names.length);
  class Node {
    constructor() {
      this.size = [100, 100];
      this.widgets = names.map((name) => {
        if (name !== "scene_prompt") return { name, options: {}, value: undefined };
        const input = new Element("textarea");
        input.value = "";
        return { name, inputEl: input, element: input, options: {}, get value() { return input.value; }, set value(value) { input.value = value; } };
      });
      this.onNodeCreated();
    }
    addDOMWidget(name, type, element, options) {
      const widget = { name, type, element, options, serialize: options.serialize };
      this.widgets.push(widget);
      return widget;
    }
    setSize(size) { this.size = size; }
    configure(info) {
      let i = 0;
      for (const widget of this.widgets) if (widget.serialize !== false) widget.value = info.widgets_values[i++];
      this.onConfigure(info);
      flush();
    }
    serialize() {
      // Reproduce the installed LiteGraph sparse positional serializer.
      const info = { widgets_values: [], widgets_values_named: {} };
      this.widgets.forEach((widget, i) => {
        if (widget.serialize === false) return;
        info.widgets_values[i] = widget.value;
        info.widgets_values_named[widget.name] = widget.value;
      });
      this.onSerialize(info);
      return plain(info);
    }
  }
  await extension.beforeRegisterNodeDef(Node, { name: type, input: {
    required: { reference_profile: [Object.values(manifest.reference_profiles)] },
    optional: { scene_preset: [manifest[kind].map((p) => p.label), { manifest_sha256: hash }] },
  } });
  const node = new Node();
  node.configure({ widgets_values: original });
  assert.deepEqual(node.serialize().widgets_values, original, `${kind}: production defaults`);
  const prompt = node.widgets.find((w) => w.name === "scene_prompt");
  assert.equal(prompt.element.tagName, "DIV");
  assert.equal(prompt.inputEl.attributes["aria-label"], "Modify this scene (optional)");
  assert.ok(prompt.options.getMinHeight() >= 190);
  const gallery = node.widgets[0];
  assert.equal(gallery.name, "visual_scene_gallery");
  assert.ok(gallery.options.getMinHeight() >= 360);
  prompt.inputEl.value = "Wear a cream knit polo and navy trousers.";
  const saved = node.serialize();
  assert.equal(saved.widgets_values[names.indexOf("scene_prompt")], prompt.inputEl.value);
  for (let i = 0; i < 3; i++) {
    node.configure(saved);
    assert.deepEqual(node.serialize(), saved, `${kind}: repeated configure retains all inputs`);
  }
  const clone = new Node();
  flush(); // Gallery can already be first before loading a workflow.
  clone.configure({ widgets_values: saved.widgets_values });
  assert.deepEqual(clone.serialize(), saved, `${kind}: clone without named values`);
  clone.configure({ widgets_values: [null, ...saved.widgets_values] });
  assert.deepEqual(clone.serialize(), saved, `${kind}: recover legacy gallery hole`);
  clone.configure({ widgets_values: [null, ...saved.widgets_values], widgets_values_named: saved.widgets_values_named });
  assert.deepEqual(clone.serialize(), saved, `${kind}: recover with named values`);
  const customCard = gallery.element.children[1].children[0];
  customCard.events.click({ preventDefault() {}, stopPropagation() {} });
  assert.equal(prompt.inputEl.attributes["aria-label"], "Describe your scene");
  assert.equal(prompt.value, "Wear a cream knit polo and navy trousers.");

  const helper = prompt.element.children[3];
  const tools = helper.children[1];
  const examples = tools.children[0];
  examples.value = "1";
  examples.events.change();
  const withClothes = prompt.value;
  assert.ok(withClothes.startsWith("Wear a cream knit polo and navy trousers."), `${kind}: examples preserve user text`);
  assert.ok(withClothes.includes("fitted black hoodie"));
  examples.value = "1";
  examples.events.change();
  assert.equal(prompt.value, withClothes, `${kind}: repeated example does not duplicate text`);
  assert.equal(examples.value, "");
  if (!isIdentity) {
    assert.equal(tools.children.length, 1, "Group has no solo angle action or Custom conversion that would replace its source photo");
    assert.equal(node.widgets.find((w) => w.name === "target_x").value, original[names.indexOf("target_x")]);
    continue;
  }

  const dog = manifest.identity.find((p) => p.label.startsWith("Dog lover"));
  const dogCard = gallery.element.children[1].children[manifest.identity.indexOf(dog)];
  const click = { preventDefault() {}, stopPropagation() {} };
  dogCard.events.click(click);
  setPrompt("Keep my black hoodie and puppy.");
  function setPrompt(value) { prompt.value = value; }
  const beforeAngle = node.serialize().widgets_values;
  const customize = tools.children[1];
  const angle = tools.children[2];
  angle.value = "right";
  angle.events.change();
  const afterAngle = node.serialize();
  assert.equal(afterAngle.widgets_values_named.scene_preset, manifest.identity[0].label);
  assert.equal(afterAngle.widgets_values_named.reference_profile, manifest.reference_profiles.solo_right);
  assert.ok(prompt.value.startsWith(dog.prompt), "Changing angle retains the complete prepared scene");
  assert.ok(prompt.value.includes("Additional scene direction: Keep my black hoodie and puppy."));
  assert.ok(prompt.value.includes("nose pointing toward the RIGHT edge"));
  assert.equal(customize.hidden, true);
  for (const name of ["seed", "appearance_polish", "fast_turbo", "control_after_generate"]) {
    assert.equal(afterAngle.widgets_values_named[name], beforeAngle[names.indexOf(name)], `${name} unchanged by angle helper`);
  }
  clone.configure(afterAngle);
  assert.deepEqual(clone.serialize(), afterAngle, "Helper settings survive save/reload");
  angle.value = "left";
  angle.events.change();
  assert.equal(node.widgets.find((w) => w.name === "reference_profile").value, manifest.reference_profiles.solo_left);
  assert.equal((prompt.value.match(/Face-angle direction:/g) || []).length, 1, "Changing sides replaces the helper's previous direction");
  assert.ok(!prompt.value.includes("nose pointing toward the RIGHT edge"));
  assert.ok(prompt.value.includes("nose pointing toward the LEFT edge"));
  const polish = node.widgets.find((w) => w.name === "appearance_polish");
  polish.value = false;
  polish.callback(false);
  assert.ok(helper.children[3].textContent.includes("Flattering appearance: off"));
  dogCard.events.click(click);
  assert.ok(helper.children[3].textContent.includes(dog.profile), "Prepared preset displays its effective reference profile");
  prompt.value = "Wear a linen shirt.";
  customize.events.click(click);
  assert.equal(prompt.value, dog.prompt + "\n\nAdditional scene direction: Wear a linen shirt.");
  assert.equal(node.widgets.find((w) => w.name === "reference_profile").value, dog.profile, "Editing a preset retains its effective references");
  const editable = prompt.value;
  customize.events.click(click);
  assert.equal(prompt.value, editable, "Custom conversion is idempotent");

  const boat = manifest.identity.find((p) => p.key === "st-barts-yacht");
  const boatCard = gallery.element.children[1].children[manifest.identity.indexOf(boat)];
  polish.value = true;
  polish.callback(true);
  boatCard.events.click(click);
  assert.equal(polish.value, false, "Boat selection uses its natural-appearance default");
  assert.ok(helper.children[3].textContent.includes("Flattering appearance: off"));
  const naturalBoat = node.serialize();
  clone.configure(naturalBoat);
  assert.deepEqual(clone.serialize(), naturalBoat, "Boat natural setting survives save/reload");
  customize.events.click(click);
  assert.equal(polish.value, false, "Editing the full boat scene retains natural appearance");
  boatCard.events.click(click);
  polish.value = true;
  polish.callback(true);
  const enhancedBoat = node.serialize();
  clone.configure(enhancedBoat);
  assert.deepEqual(clone.serialize(), enhancedBoat, "Explicit user override survives reload");
  dogCard.events.click(click);
  assert.equal(polish.value, true, "Cards without an appearance default keep the user's choice");
}
console.log("PASS: Identity/Group prompt binding, examples, preset retention, angle/reference changes, status, defaults and save/reload/clone migration.");
