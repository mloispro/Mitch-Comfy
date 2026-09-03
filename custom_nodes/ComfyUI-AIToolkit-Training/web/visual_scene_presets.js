const { app } = window.comfyAPI.app;

const STYLE_ID = "mitch-klein9b-visual-preset-styles";
const ASSET_ROOT = new URL("./assets/scene-presets/", import.meta.url);
const ASSET_VERSION = "20260903-generated-previews-v2";
const MANIFEST_URL = new URL("./assets/scene-presets/manifest.json", import.meta.url);
MANIFEST_URL.searchParams.set("v", ASSET_VERSION);
let manifestPromise;

async function loadManifest() {
  manifestPromise ??= fetch(MANIFEST_URL).then(async (response) => {
    if (!response.ok) throw new Error(`Preset manifest request failed: ${response.status}`);
    const manifest = await response.json();
    if (manifest.schema_version !== 1) throw new Error("Unsupported preset manifest schema");
    if (!Array.isArray(manifest.identity) || !Array.isArray(manifest.group)) {
      throw new Error("Preset manifest is missing Identity or Group records");
    }
    return manifest;
  });
  return manifestPromise;
}

function ensureStyles() {
  if (document.getElementById(STYLE_ID)) return;
  const style = document.createElement("style");
  style.id = STYLE_ID;
  style.textContent = `
    .mitch-preset-root {
      width: 100%; height: 100%; min-height: 540px; box-sizing: border-box;
      display: flex; flex-direction: column; gap: 8px; padding: 8px;
      background: #121719; border: 1px solid #354347; border-radius: 8px;
      color: #e8eeee; font: 13px/1.3 Arial, sans-serif; overflow: hidden;
    }
    .mitch-preset-heading { display:flex; justify-content:space-between; align-items:baseline; gap:10px; }
    .mitch-preset-heading strong { color:#f2f7f7; font-size:15px; }
    .mitch-preset-heading span { color:#9db0b5; font-size:11px; text-align:right; }
    .mitch-preset-grid {
      flex: 1 1 auto; min-height: 0; overflow-y: auto; padding: 2px;
      display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px;
    }
    .mitch-preset-card {
      position:relative; min-width:0; padding:0; overflow:hidden; cursor:pointer;
      border:2px solid #334247; border-radius:7px; background:#1b2326; color:#e9efef;
      text-align:left; transition:border-color .12s, transform .12s, box-shadow .12s;
    }
    .mitch-preset-card:hover { border-color:#86aeb5; transform:translateY(-1px); }
    .mitch-preset-card.selected { border-color:#69d8b1; box-shadow:0 0 0 2px rgba(105,216,177,.22); }
    .mitch-preset-card img { width:100%; aspect-ratio:10/7; display:block; object-fit:cover; background:#222; }
    .mitch-preset-card span {
      display:block; min-height:34px; padding:6px 7px; box-sizing:border-box;
      font-size:11px; line-height:1.18; color:#f2f5f5;
    }
    .mitch-preset-check {
      display:none; position:absolute; top:6px; right:6px; width:23px; height:23px;
      border-radius:50%; background:#48c99a; color:#082118; font-weight:bold;
      align-items:center; justify-content:center; box-shadow:0 1px 5px #000a;
    }
    .mitch-preset-card.selected .mitch-preset-check { display:flex; }
    .mitch-preset-status { color:#aedacb; font-size:12px; min-height:16px; }
  `;
  document.head.appendChild(style);
}

function hideSerializedCombo(widget) {
  widget.hidden = true;
  widget.computeSize = () => [0, -4];
}

function setWidgetValue(node, name, value) {
  const widget = node.widgets?.find((item) => item.name === name);
  if (!widget) return;
  widget.value = value;
  widget.callback?.(value, node, widget);
}

function installGallery(node, presets, kind) {
  ensureStyles();
  const presetWidget = node.widgets?.find((item) => item.name === "scene_preset");
  if (!presetWidget || node.__mitchPresetGallery) return;
  node.__mitchPresetGallery = true;
  hideSerializedCombo(presetWidget);

  const root = document.createElement("div");
  root.className = "mitch-preset-root";
  const heading = document.createElement("div");
  heading.className = "mitch-preset-heading";
  const title = document.createElement("strong");
  title.textContent = kind === "identity" ? "Choose a solo scene visually" : "Choose a group layout visually";
  const help = document.createElement("span");
  help.textContent = "Click a card; Custom uses the text/upload controls below";
  heading.append(title, help);
  root.appendChild(heading);

  const grid = document.createElement("div");
  grid.className = "mitch-preset-grid";
  root.appendChild(grid);
  const status = document.createElement("div");
  status.className = "mitch-preset-status";
  root.appendChild(status);

  const cards = new Map();
  const refresh = () => {
    const value = presetWidget.value;
    for (const [label, card] of cards) card.classList.toggle("selected", label === value);
    const selected = presets.find((item) => item.label === value);
    if (!selected) return;
    status.textContent = `Selected: ${selected.label}`;
  };

  for (const preset of presets) {
    const card = document.createElement("button");
    card.type = "button";
    card.className = "mitch-preset-card";
    card.title = `Select ${preset.label}`;
    const image = document.createElement("img");
    const imageUrl = new URL(preset.thumbnail, ASSET_ROOT);
    imageUrl.searchParams.set("v", ASSET_VERSION);
    image.src = imageUrl.href;
    image.alt = preset.label;
    image.loading = "lazy";
    image.draggable = false;
    const label = document.createElement("span");
    label.textContent = preset.label;
    const check = document.createElement("span");
    check.className = "mitch-preset-check";
    check.textContent = "✓";
    card.append(image, label, check);
    card.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      presetWidget.value = preset.label;
      presetWidget.callback?.(preset.label, node, presetWidget);
      if (kind === "identity") {
        setWidgetValue(node, "reference_profile", preset.profile);
      } else if (preset.key !== "custom-group") {
        setWidgetValue(node, "target_x", preset.target_x);
        setWidgetValue(node, "target_y", preset.target_y);
        setWidgetValue(node, "head_scale", preset.head_scale);
      }
      refresh();
      node.setDirtyCanvas?.(true, true);
      app.graph?.setDirtyCanvas?.(true, true);
    });
    cards.set(preset.label, card);
    grid.appendChild(card);
  }

  const galleryWidget = node.addDOMWidget("visual_scene_gallery", "div", root, {
    serialize: false,
    hideOnZoom: false,
  });
  const moveGalleryFirst = () => {
    const index = node.widgets.indexOf(galleryWidget);
    if (index > 0) {
      node.widgets.splice(index, 1);
      node.widgets.unshift(galleryWidget);
    }
  };
  node.setSize([kind === "identity" ? 920 : 820, kind === "identity" ? 1120 : 850]);

  const previousConfigure = node.onConfigure;
  node.onConfigure = function (...args) {
    const result = previousConfigure?.apply(this, args);
    // Comfy assigns saved widget values by the widget order that exists during
    // configure. Move the non-serialized gallery only after that assignment so
    // it can appear first without shifting the real input values by one slot.
    setTimeout(() => {
      moveGalleryFirst();
      refresh();
    }, 0);
    return result;
  };
  setTimeout(() => {
    moveGalleryFirst();
    refresh();
  }, 0);
}

app.registerExtension({
  name: "Mitch.Klein9BVisualScenePresets",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    const kind =
      nodeData?.name === "Flux2Klein9BMitchIdentityStudioVisualPresetsV11"
        ? "identity"
        : nodeData?.name === "Flux2Klein9BMitchGroupSceneStudioVisualPresetsV11"
          ? "group"
          : null;
    if (!kind) return;
    const manifest = await loadManifest();
    const presets = kind === "identity" ? manifest.identity : manifest.group;
    const previousCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function (...args) {
      const result = previousCreated?.apply(this, args);
      installGallery(this, presets, kind);
      return result;
    };
  },
});
