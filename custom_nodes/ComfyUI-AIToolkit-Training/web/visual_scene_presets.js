const { app } = window.comfyAPI.app;

const STYLE_ID = "mitch-klein9b-visual-preset-styles";
const ASSET_ROOT = new URL("./assets/scene-presets/", import.meta.url);

const IDENTITY_PRESETS = [
  ["Custom — write your own scene", "identity-custom.jpg", "SOLO — front + right-facing angle"],
  ["Founder editorial — modern studio", "identity-founder-editorial.jpg", "SOLO — front + right-facing angle"],
  ["Cooking candid — warm modern kitchen", "identity-cooking-candid.jpg", "SOLO — front + right-facing angle"],
  ["Golden-hour rooftop — linen shirt", "identity-golden-hour-rooftop.jpg", "SOLO — front + right-facing angle"],
  ["Night city balcony — black open-collar shirt", "identity-night-city-balcony.jpg", "SOLO — front + right-facing angle"],
  ["Rooftop cocktail — city lights", "identity-rooftop-cocktail.jpg", "SOLO — front + left-facing angle"],
  ["Amalfi balcony — white linen", "identity-amalfi-balcony.jpg", "SOLO — front + right-facing angle"],
  ["Italian lake boat — relaxed travel", "identity-italian-lake-boat.jpg", "FULL BODY — front + body proportions"],
  ["Elegant restaurant — understated evening", "identity-elegant-restaurant.jpg", "SOLO — front + right-facing angle"],
  ["Cat lover — Ragdoll", "identity-ragdoll-cat.jpg", "SOLO — front + left-facing angle"],
  ["Toddler moment — warm family candid", "identity-toddler-moment.jpg", "GROUP — front only (one Mitch)"],
  ["Dog lover — small Golden Shepherd puppy", "identity-golden-shepherd-puppy.jpg", "SOLO — front + left-facing angle"],
  ["Golf course — tropical morning", "identity-golf-course.jpg", "FULL BODY — front + body proportions"],
  ["Weekend lake — fitted T-shirt", "identity-weekend-lake.jpg", "FULL BODY — front + body proportions"],
  ["Downtown menswear — sunrise", "identity-downtown-menswear.jpg", "FULL BODY — front + body proportions"],
].map(([label, thumbnail, profile]) => ({ label, thumbnail, profile }));

const GROUP_PRESETS = [
  ["Custom — uploaded group photo", "group-custom.jpg", 0.50, 0.44, 0.92],
  ["Approved lounge — central Mitch", "group-approved-lounge.jpg", 0.50, 0.44, 0.92],
  ["Night out A — corner booth", "group-night-out-a.jpg", 0.52, 0.30, 0.92],
  ["Night out B — group booth", "group-night-out-b.jpg", 0.46, 0.33, 0.92],
  ["Amber booth — four friends", "group-amber-booth.jpg", 0.51, 0.45, 0.92],
].map(([label, thumbnail, targetX, targetY, headScale]) => ({
  label,
  thumbnail,
  targetX,
  targetY,
  headScale,
}));

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
    image.src = new URL(preset.thumbnail, ASSET_ROOT).href;
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
      } else if (preset.label !== "Custom — uploaded group photo") {
        setWidgetValue(node, "target_x", preset.targetX);
        setWidgetValue(node, "target_y", preset.targetY);
        setWidgetValue(node, "head_scale", preset.headScale);
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
    const previousCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function (...args) {
      const result = previousCreated?.apply(this, args);
      installGallery(this, kind === "identity" ? IDENTITY_PRESETS : GROUP_PRESETS, kind);
      return result;
    };
  },
});
