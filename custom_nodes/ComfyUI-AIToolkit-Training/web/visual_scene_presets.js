const { app } = window.comfyAPI.app;

const STYLE_ID = "mitch-klein9b-visual-preset-styles";
const ASSET_ROOT = new URL("./assets/scene-presets/", import.meta.url);
const ASSET_VERSION = "20260920-boat-exact-foreground-v5";
const MANIFEST_URL = new URL("./assets/scene-presets/manifest.json", import.meta.url);
MANIFEST_URL.searchParams.set("v", ASSET_VERSION);
let manifestPromise;

async function fetchManifest() {
  const response = await fetch(MANIFEST_URL, { cache: "no-store" });
  if (!response.ok) throw new Error(`Preset manifest request failed: ${response.status}`);
  const bytes = await response.arrayBuffer();
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  const sha256 = Array.from(new Uint8Array(digest), (byte) =>
    byte.toString(16).padStart(2, "0"),
  ).join("").toUpperCase();
  const manifest = JSON.parse(new TextDecoder().decode(bytes));
  if (manifest.schema_version !== 1) throw new Error("Unsupported preset manifest schema");
  if (!Array.isArray(manifest.identity) || !Array.isArray(manifest.group)) {
    throw new Error("Preset manifest is missing Identity or Group records");
  }
  Object.defineProperty(manifest, "__sha256", { value: sha256 });
  return manifest;
}

async function loadManifest() {
  if (!manifestPromise) {
    manifestPromise = (async () => {
      let lastError;
      for (let attempt = 0; attempt < 2; attempt += 1) {
        try {
          return await fetchManifest();
        } catch (error) {
          lastError = error;
          if (attempt === 0) {
            await new Promise((resolve) => setTimeout(resolve, 250));
          }
        }
      }
      throw lastError;
    })()
      .catch((error) => {
        manifestPromise = undefined;
        throw error;
      });
  }
  return manifestPromise;
}

function assertLiveManifestParity(nodeData, presets, kind, manifest) {
  const livePresetChoices = nodeData?.input?.optional?.scene_preset?.[0];
  const liveManifestSha256 = nodeData?.input?.optional?.scene_preset?.[1]?.manifest_sha256;
  const manifestLabels = presets.map((preset) => preset.label);
  if (
    !Array.isArray(livePresetChoices) ||
    JSON.stringify(livePresetChoices) !== JSON.stringify(manifestLabels)
  ) {
    throw new Error(`${kind} preset choices do not match the live Python manifest`);
  }
  if (
    typeof liveManifestSha256 !== "string" ||
    liveManifestSha256.toUpperCase() !== manifest.__sha256
  ) {
    throw new Error(`${kind} preset manifest hash does not match the live Python node`);
  }
  if (kind !== "identity") return;
  const liveProfileChoices = nodeData?.input?.required?.reference_profile?.[0];
  const manifestProfiles = Object.values(manifest.reference_profiles ?? {});
  if (
    !Array.isArray(liveProfileChoices) ||
    manifestProfiles.some((profile) => !liveProfileChoices.includes(profile))
  ) {
    throw new Error("Identity reference profiles do not match the live Python node");
  }
}

function thumbnailUrl(preset) {
  const url = new URL(preset.thumbnail, ASSET_ROOT);
  if (!url.href.startsWith(ASSET_ROOT.href)) {
    throw new Error(`Preset thumbnail escapes the visual asset root: ${preset.thumbnail}`);
  }
  url.searchParams.set("v", ASSET_VERSION);
  return url.href;
}

function ensureStyles() {
  if (document.getElementById(STYLE_ID)) return;
  const style = document.createElement("style");
  style.id = STYLE_ID;
  style.textContent = `
    .mitch-preset-root {
      width: 100%; height: 100%; min-height: 0; box-sizing: border-box;
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
      grid-auto-rows: max-content; align-content: start;
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
    .mitch-preset-card .mitch-preset-check {
      display:none; position:absolute; top:6px; right:6px; width:23px; height:23px;
      border-radius:50%; background:#48c99a; color:#082118; font-weight:bold;
      align-items:center; justify-content:center; box-shadow:0 1px 5px #000a;
    }
    .mitch-preset-card.selected .mitch-preset-check { display:flex; }
    .mitch-preset-status { color:#aedacb; font-size:12px; min-height:16px; }
    .mitch-scene-prompt-root {
      display:flex; flex-direction:column; gap:7px; box-sizing:border-box;
      width:100%; height:100%; min-height:0; padding:8px;
      background:#121719; border:1px solid #698a7e; border-radius:8px;
      color:#edf5f2; font:14px/1.3 Arial,sans-serif;
    }
    .mitch-scene-prompt-root textarea {
      flex:1 1 auto; width:100%; height:auto; min-height:80px; resize:none;
      box-sizing:border-box; padding:8px; font:14px/1.4 Arial,sans-serif;
    }
    .mitch-scene-prompt-root small { color:#adbfba; font-size:12px; }
    .mitch-prompt-helper { display:flex; flex-direction:column; gap:6px; border-top:1px solid #354347; padding-top:7px; }
    .mitch-prompt-tools { display:flex; flex-wrap:wrap; align-items:center; gap:6px; }
    .mitch-prompt-tools button, .mitch-prompt-tools select {
      max-width:100%; padding:6px 8px; border:1px solid #698a7e; border-radius:5px;
      background:#23332e; color:#edf5f2; font:12px Arial,sans-serif; cursor:pointer;
    }
    .mitch-prompt-tools button:hover { background:#345045; }
    .mitch-prompt-tools button:focus-visible, .mitch-prompt-tools select:focus-visible { outline:2px solid #69d8b1; }
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

const PROMPT_EXAMPLES = [
  ["Hair", "Give Mitch a neat textured side part with tidy sides and natural volume, keeping his recognizable hairline."],
  ["Clothes", "Dress Mitch in a fitted black hoodie with natural fabric folds."],
  ["Flattering expression", "Give Mitch a relaxed brow, rested open eyes, neatly groomed stubble and a confident closed-mouth smile, keeping his recognizable features."],
  ["Hands (holding a puppy)", "Mitch holds the puppy close to his chest. One hand supports its chest and the other cups its hindquarters, with two separate wrists and naturally curved fingers."],
];

function labelScenePrompt(node, presets, kind, profiles, refreshGallery) {
  const widget = node.widgets?.find((item) => item.name === "scene_prompt");
  const input = widget?.inputEl ?? widget?.element;
  if (!input || input.tagName !== "TEXTAREA") return () => {};
  const root = document.createElement("div");
  root.className = "mitch-scene-prompt-root";
  const title = document.createElement("strong");
  const help = document.createElement("small");
  root.append(title, input, help);
  const helper = document.createElement("div");
  helper.className = "mitch-prompt-helper";
  const helperTitle = document.createElement("strong");
  helperTitle.textContent = "Prompt helper";
  const tools = document.createElement("div");
  tools.className = "mitch-prompt-tools";
  helper.append(helperTitle, tools);
  root.appendChild(helper);
  const presetWidget = node.widgets.find((item) => item.name === "scene_preset");
  const selectedPreset = () => presets.find((item) => item.label === presetWidget.value);
  const customPreset = presets.find((item) => item.key === "custom" || item.key === "custom-group");
  const isCustom = (preset) => preset?.label === customPreset.label;
  const edit = (action) => {
    app.graph?.beforeChange?.();
    try {
      action();
      refreshGallery();
      node.setDirtyCanvas?.(true, true);
      app.graph?.setDirtyCanvas?.(true, true);
    } finally {
      app.graph?.afterChange?.();
    }
  };
  const appendText = (text) => {
    const current = String(widget.value ?? "").trim();
    if (!current.includes(text)) setWidgetValue(node, "scene_prompt", [current, text].filter(Boolean).join("\n\n"));
  };
  // Match the backend's preset + extra-direction composition before switching
  // to Custom. The complete editable text must survive save/reload and undo.
  const makeEditable = () => {
    const selected = selectedPreset();
    if (!selected || isCustom(selected)) return;
    const extra = String(widget.value ?? "").trim();
    setWidgetValue(node, "scene_prompt", selected.prompt + (extra ? `\n\nAdditional scene direction: ${extra}` : ""));
    setWidgetValue(node, "reference_profile", selected.profile);
    setWidgetValue(node, "scene_preset", customPreset.label);
  };
  const examples = document.createElement("select");
  examples.setAttribute("aria-label", "Add a prompt example");
  for (const [value, label] of [["", "Add an editable example…"], ...PROMPT_EXAMPLES.map(([label], index) => [String(index), label])]) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    examples.appendChild(option);
  }
  examples.value = "";
  examples.addEventListener("change", () => {
    const example = examples.value === "" ? null : PROMPT_EXAMPLES[Number(examples.value)];
    if (example) edit(() => appendText(example[1]));
    examples.value = "";
  });
  tools.appendChild(examples);
  let customize;
  if (kind === "identity") {
    customize = document.createElement("button");
    customize.type = "button";
    customize.textContent = "Edit full preset scene";
    customize.title = "Copies this scene and your added prompt into Custom, so you can replace conflicting instructions.";
    customize.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      edit(makeEditable);
    });
    tools.appendChild(customize);
    const angle = document.createElement("select");
    angle.setAttribute("aria-label", "Face angle — keeps scene and switches to Custom");
    for (const [value, label] of [["", "Choose face angle…"], ["left", "Nose toward picture LEFT"], ["right", "Nose toward picture RIGHT"]]) {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = label;
      angle.appendChild(option);
    }
    angle.value = "";
    angle.addEventListener("change", () => {
      const side = angle.value;
      if (side !== "left" && side !== "right") return;
      edit(() => {
        makeEditable();
        setWidgetValue(node, "reference_profile", profiles[`solo_${side}`]);
        // Replace only this helper's own direction line when changing sides.
        // User-authored prose remains editable; never guess which text to delete.
        const current = String(widget.value ?? "").replace(/^Face-angle direction:.*(?:\r?\n|$)/gm, "").trim();
        setWidgetValue(node, "scene_prompt", current);
        appendText(`Face-angle direction: Turn Mitch's head gently toward picture-${side.toUpperCase()}, with his nose pointing toward the ${side.toUpperCase()} edge of the image, matching the angle in Picture 2.`);
      });
      angle.value = "";
    });
    tools.appendChild(angle);
  }
  const guidance = document.createElement("small");
  guidance.textContent = kind === "identity"
    ? "Edit examples to suit your photo. Use picture-left/right for the nose; describe gaze separately. Replace any conflicting pose or clothing text. For hands, say what each hand supports; wording cannot guarantee anatomy."
    : "Edit examples to suit your photo. Name Mitch when changing hair, clothes or expression. The source photo guides the group layout; large pose changes may conflict with it. For hands, describe simple contact.";
  const state = document.createElement("small");
  state.setAttribute("aria-live", "polite");
  helper.append(guidance, state);
  // Reuse the original textarea and its existing getValue/setValue callbacks.
  // This adds a visible label without adding a serialized field or moving it.
  widget.element = root;
  widget.options.getMinHeight = () => 350;
  widget.options.getMaxHeight = () => 400;
  widget.options.hideOnZoom = false;
  return (custom) => {
    const label = custom ? "Describe your scene" : "Modify this scene (optional)";
    title.textContent = label;
    widget.label = label;
    input.setAttribute("aria-label", label);
    input.placeholder = custom
      ? "Describe the complete photo: clothes, pose, setting and lighting."
      : "Example: Keep this setting and pose. Wear a cream knit polo and navy trousers.";
    help.textContent = custom
      ? "Required for Custom. Your genuine identity references still apply."
      : "Added to the selected preset. Leave blank to use it unchanged.";
    if (customize) customize.hidden = custom;
    const polish = node.widgets.find((item) => item.name === "appearance_polish");
    const profile = custom
      ? node.widgets.find((item) => item.name === "reference_profile")?.value
      : selectedPreset()?.profile;
    state.textContent = (kind === "identity"
      ? `${custom ? "Using" : "Preset uses"}: ${profile}. ${custom ? "" : "Choosing a face angle keeps this scene in Custom. "}`
      : "") + `Flattering appearance: ${polish?.value ? "on" : "off"}. Use the switch below to change it.`;
  };
}

function installGallery(node, presets, kind, profiles) {
  ensureStyles();
  const presetWidget = node.widgets?.find((item) => item.name === "scene_preset");
  if (!presetWidget || node.__mitchPresetGallery) return;
  node.__mitchPresetGallery = true;
  // Keep the Python input order separate from the gallery's visual position.
  const inputWidgets = [...node.widgets];
  hideSerializedCombo(presetWidget);
  const refreshPromptLabel = labelScenePrompt(node, presets, kind, profiles, () => refresh());

  const root = document.createElement("div");
  root.className = "mitch-preset-root";
  const heading = document.createElement("div");
  heading.className = "mitch-preset-heading";
  const title = document.createElement("strong");
  title.textContent = kind === "identity" ? "Choose a solo scene visually" : "Choose a group layout visually";
  const help = document.createElement("span");
  help.textContent = "Choose a card, then use the Modify this scene box below";
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
    refreshPromptLabel(selected.key === "custom" || selected.key === "custom-group");
  };
  for (const name of ["reference_profile", "appearance_polish"]) {
    const widget = node.widgets.find((item) => item.name === name);
    if (!widget) continue;
    if (name === "appearance_polish") widget.label = "Flattering appearance";
    const callback = widget.callback;
    widget.callback = function (...args) {
      const result = callback?.apply(this, args);
      refresh();
      return result;
    };
  }

  for (const preset of presets) {
    const card = document.createElement("button");
    card.type = "button";
    card.className = "mitch-preset-card";
    card.title = `Select ${preset.label}`;
    const image = document.createElement("img");
    image.src = thumbnailUrl(preset);
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
        if (preset.key !== "custom") {
          setWidgetValue(node, "reference_profile", preset.profile);
          if (typeof preset.appearance_polish_default === "boolean") {
            setWidgetValue(node, "appearance_polish", preset.appearance_polish_default);
          }
        }
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
    // ComfyUI's layout reads these hooks, not the CSS min-height. A CSS-only
    // minimum let the gallery paint over the following prompt and toggles.
    getMinHeight: () => kind === "identity" ? 460 : 360,
    getMaxHeight: () => kind === "identity" ? 460 : 360,
  });
  const moveGalleryFirst = () => {
    const index = node.widgets.indexOf(galleryWidget);
    if (index > 0) {
      node.widgets.splice(index, 1);
      node.widgets.unshift(galleryWidget);
    }
    // Recompute the layout after changing visual widget order, including when
    // saved dimensions or output previews were restored during configuration.
    node.setSize([Math.max(node.size[0], kind === "identity" ? 920 : 820),
      Math.max(node.size[1], kind === "identity" ? 1120 : 1000)]);
  };
  node.setSize([kind === "identity" ? 920 : 820, kind === "identity" ? 1120 : 850]);

  const previousConfigure = node.onConfigure;
  node.onConfigure = function (...args) {
    const result = previousConfigure?.apply(this, args);
    const info = args[0];
    let values = info?.widgets_values;
    // Older frontend saves left a null slot for the non-serialized gallery.
    // Accept that layout as well as the original production workflow files.
    if (values?.length === inputWidgets.length + 1 && values[0] == null) {
      values = values.slice(1);
    }
    inputWidgets.forEach((widget, index) => {
      if (Object.hasOwn(info?.widgets_values_named ?? {}, widget.name)) {
        widget.value = info.widgets_values_named[widget.name];
      } else if (values && index < values.length) {
        widget.value = values[index];
      }
    });
    setTimeout(() => {
      moveGalleryFirst();
      refresh();
    }, 0);
    return result;
  };
  const previousSerialize = node.onSerialize;
  node.onSerialize = function (info) {
    const result = previousSerialize?.call(this, info);
    // LiteGraph versions differ on whether a non-serialized widget leaves a
    // positional hole. Always save the original Python widget order, so a
    // reload, undo or clone cannot put reference_profile into scene_prompt.
    info.widgets_values = inputWidgets.map((widget) => widget.value ?? null);
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
    assertLiveManifestParity(nodeData, presets, kind, manifest);
    const previousCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function (...args) {
      const result = previousCreated?.apply(this, args);
      installGallery(this, presets, kind, manifest.reference_profiles);
      return result;
    };
  },
});
