const form = document.getElementById("asset-form");
const imageInput = document.getElementById("image-input");
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

function syncRangeLabels() {
  heightScaleValue.textContent = Number(heightScaleInput.value).toFixed(2);
  baseThicknessValue.textContent = Number(baseThicknessInput.value).toFixed(2);
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
syncRangeLabels();

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (!imageInput.files.length) {
    statusText.textContent = "Please choose an image first.";
    return;
  }

  const payload = new FormData();
  payload.append("image", imageInput.files[0]);
  payload.append("resolution", resolutionInput.value);
  payload.append("height_scale", heightScaleInput.value);
  payload.append("base_thickness", baseThicknessInput.value);

  submitButton.disabled = true;
  statusText.textContent = "Analyzing image tones, building depth, and packaging the 3D asset...";
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
    previewImage.src = data.preview_url;
    grayRenderImage.src = data.gray_render_url;
    assetLink.href = data.asset_url;
    textureLink.href = data.texture_url;
    grayRenderLink.href = data.gray_render_url;
    metadataLink.href = data.metadata_url;
    vertexCount.textContent = data.vertex_count.toLocaleString();
    faceCount.textContent = data.face_count.toLocaleString();
    resolutionValue.textContent = `${data.resolution} px`;
    heightValue.textContent = Number(data.height_scale).toFixed(2);
    baseValue.textContent = Number(data.base_thickness).toFixed(2);
    statusText.textContent = `Asset generated successfully. Job ID: ${data.job_id}`;
    resultCard.classList.remove("hidden");
  } catch (error) {
    statusText.textContent = error.message || "An unexpected error occurred.";
  } finally {
    submitButton.disabled = false;
  }
});
