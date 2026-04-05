const form = document.getElementById("asset-form");
const imageInput = document.getElementById("image-input");
const submitButton = document.getElementById("submit-button");
const statusText = document.getElementById("status-text");
const resultCard = document.getElementById("result-card");
const resultSummary = document.getElementById("result-summary");
const previewImage = document.getElementById("preview-image");
const assetLink = document.getElementById("asset-link");
const textureLink = document.getElementById("texture-link");
const vertexCount = document.getElementById("vertex-count");
const faceCount = document.getElementById("face-count");

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (!imageInput.files.length) {
    statusText.textContent = "Please choose an image first.";
    return;
  }

  const payload = new FormData();
  payload.append("image", imageInput.files[0]);

  submitButton.disabled = true;
  statusText.textContent = "Generating a 3D asset package from the uploaded image...";
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
    assetLink.href = data.asset_url;
    textureLink.href = data.texture_url;
    vertexCount.textContent = data.vertex_count.toLocaleString();
    faceCount.textContent = data.face_count.toLocaleString();
    statusText.textContent = `Asset generated successfully. Job ID: ${data.job_id}`;
    resultCard.classList.remove("hidden");
  } catch (error) {
    statusText.textContent = error.message || "An unexpected error occurred.";
  } finally {
    submitButton.disabled = false;
  }
});
