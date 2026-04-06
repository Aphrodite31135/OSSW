const form = document.getElementById("asset-form");
const modeImage = document.getElementById("mode-image");
const modeText = document.getElementById("mode-text");
const imageInput = document.getElementById("image-input");
const promptPanel = document.getElementById("prompt-panel");
const promptInput = document.getElementById("prompt-input");
const resolutionInput = document.getElementById("resolution-input");
const heightScaleInput = document.getElementById("height-scale-input");
const baseThicknessInput = document.getElementById("base-thickness-input");
const heightScaleValue = document.getElementById("height-scale-value");
const baseThicknessValue = document.getElementById("base-thickness-value");
const sourcePreview = document.getElementById("source-preview");
const sourceImage = document.getElementById("source-image");
const submitButton = document.getElementById("submit-button");
const statusText = document.getElementById("status-text");
const resultCard = document.getElementById("result-card");
const resultSummary = document.getElementById("result-summary");
const previewImage = document.getElementById("preview-image");
const grayRenderImage = document.getElementById("gray-render-image");
const assetLink = document.getElementById("asset-link");
const textureLink = document.getElementById("texture-link");
const grayRenderLink = document.getElementById("gray-render-link");
const metadataLink = document.getElementById("metadata-link");
const vertexCount = document.getElementById("vertex-count");
const faceCount = document.getElementById("face-count");
const resolutionValue = document.getElementById("resolution-value");
const heightValue = document.getElementById("height-value");
const baseValue = document.getElementById("base-value");

function currentMode() {
  return modeText.checked ? "text" : "image";
}

function setLinkState(element, href) {
  if (href) {
    element.href = href;
    element.classList.remove("hidden");
  } else {
    element.removeAttribute("href");
    element.classList.add("hidden");
  }
}

function setImageState(element, src) {
  if (src) {
    element.src = src;
    element.parentElement.classList.remove("hidden");
  } else {
    element.removeAttribute("src");
    element.parentElement.classList.add("hidden");
  }
}

function syncRangeLabels() {
  heightScaleValue.textContent = Number(heightScaleInput.value).toFixed(2);
  baseThicknessValue.textContent = Number(baseThicknessInput.value).toFixed(2);
}

function syncSourceMode() {
  const textMode = currentMode() === "text";
  promptPanel.classList.toggle("hidden", !textMode);
  imageInput.required = !textMode;
  if (textMode) {
    imageInput.value = "";
    sourcePreview.classList.add("hidden");
    sourceImage.removeAttribute("src");
  }
}

function showSourcePreview(file) {
  if (!file) {
    sourcePreview.classList.add("hidden");
    sourceImage.removeAttribute("src");
    return;
  }

  sourceImage.src = URL.createObjectURL(file);
  sourcePreview.classList.remove("hidden");
}

heightScaleInput.addEventListener("input", syncRangeLabels);
baseThicknessInput.addEventListener("input", syncRangeLabels);
imageInput.addEventListener("change", () => showSourcePreview(imageInput.files[0]));
modeImage.addEventListener("change", syncSourceMode);
modeText.addEventListener("change", syncSourceMode);
syncRangeLabels();
syncSourceMode();

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (currentMode() === "image" && !imageInput.files.length) {
    statusText.textContent = "Please choose an image first.";
    return;
  }
  if (currentMode() === "text" && !promptInput.value.trim()) {
    statusText.textContent = "Please enter a prompt first.";
    return;
  }

  const payload = new FormData();
  payload.append("source_mode", currentMode());
  payload.append("prompt", promptInput.value.trim());
  if (imageInput.files.length) {
    payload.append("image", imageInput.files[0]);
  }
  payload.append("resolution", resolutionInput.value);
  payload.append("height_scale", heightScaleInput.value);
  payload.append("base_thickness", baseThicknessInput.value);

  submitButton.disabled = true;
  statusText.textContent = currentMode() === "text"
    ? "Generating a source image from text, sending it to Hunyuan3D, and packaging the GLB result..."
    : "Sending the image to Hunyuan3D, generating a GLB model, and packaging the result...";
  resultCard.classList.add("hidden");

  try {
    const response = await fetch("/api/generate-asset", {
      method: "POST",
      body: payload,
    });

    if (!response.ok) {
      const data = await response.json();
      throw new Error(data.detail || "Generation failed.");
    }

    const data = await response.json();
    resultSummary.textContent = data.summary;
    if (data.source_image_url) {
      setImageState(sourceImage, data.source_image_url);
      sourcePreview.classList.remove("hidden");
    }
    setImageState(previewImage, data.preview_url);
    setImageState(grayRenderImage, data.gray_render_url);
    setLinkState(assetLink, data.asset_url);
    setLinkState(textureLink, data.texture_url);
    setLinkState(grayRenderLink, data.gray_render_url);
    setLinkState(metadataLink, data.metadata_url);
    vertexCount.textContent = data.vertex_count ? data.vertex_count.toLocaleString() : "-";
    faceCount.textContent = data.face_count ? data.face_count.toLocaleString() : "-";
    resolutionValue.textContent = data.resolution ? `${data.resolution} px` : data.asset_format.toUpperCase();
    heightValue.textContent = data.height_scale ? Number(data.height_scale).toFixed(2) : data.backend;
    baseValue.textContent = data.prompt ? "prompt" : (data.base_thickness ? Number(data.base_thickness).toFixed(2) : "-");
    statusText.textContent = `Asset generated successfully. Job ID: ${data.job_id} (${data.source_mode} -> ${data.backend})`;
    resultCard.classList.remove("hidden");
  } catch (error) {
    statusText.textContent = error.message || "An unexpected error occurred.";
  } finally {
    submitButton.disabled = false;
  }
});
