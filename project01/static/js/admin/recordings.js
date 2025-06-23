const RECORDINGS_PER_LOAD = 5;
let currentPage = 1;
let isLoading = false;
let hasMoreRecordings = true;
let recordingsContainer; // now global

document.addEventListener("DOMContentLoaded", () => {
  recordingsContainer = document.getElementById("recordingsContainer");
  if (!recordingsContainer) {
    console.error("Error: recordingsContainer not found");
    return;
  }

  loadFilterOptions();
  initRecordingsTimeline();
});

// Fetch filters
async function loadFilterOptions() {
  const res = await fetch("/api/filters");
  const { nvrs, cameras } = await res.json();

  const nvrSelect = document.getElementById("nvrSelect");
  const cameraSelect = document.getElementById("cameraSelect");

  nvrs.forEach((nvr) => {
    const option = document.createElement("option");
    option.value = nvr.id;
    option.textContent = nvr.area_name;
    nvrSelect.appendChild(option);
  });

  function populateCameraOptions(selectedNvrId) {
    cameraSelect.innerHTML = '<option value="all">All Cameras</option>';
    cameras.forEach((cam) => {
      if (selectedNvrId === "all" || cam.nvr_id == selectedNvrId) {
        const option = document.createElement("option");
        option.value = cam.id;
        option.textContent = `${cam.channel} (${
          nvrs.find((n) => n.id === cam.nvr_id)?.area_name || "Unknown"
        })`;
        cameraSelect.appendChild(option);
      }
    });
  }

  populateCameraOptions("all");
  cameraSelect.value = "all";

  nvrSelect.addEventListener("change", () => {
    populateCameraOptions(nvrSelect.value);
  });
}

// Fetch recordings (now globally available)
function fetchRecordings(page, limit) {
  const nvr = document.getElementById("nvrSelect").value;
  const camera = document.getElementById("cameraSelect").value;
  const startDate = document.getElementById("startDate").value;
  const endDate = document.getElementById("endDate").value;

  const params = new URLSearchParams({
    page,
    limit,
    nvr,
    camera,
    start: startDate,
    end: endDate,
  });

  return fetch(`/api/recordings?${params}`).then((res) => res.json());
}

function createRecordingDateElement(recordingDay) {
  const recordingItem = document.createElement("div");
  recordingItem.className = "recording-item mb-4";

  let videosHTML = "";
  recordingDay.videos.forEach((video) => {
    videosHTML += `
    <div class="col-4">
      <div class="card position-relative">
        <video
         autoplay
          muted
          loop
          playsinline
          src="${video.src}" 
          class="video-thumb"
          data-id="${video.id}"
          data-size="${video.size}" 
          data-duration="${video.duration}" 
          data-camera-id="${video.cameraId}" 
          data-date="${video.fullDate}" 
          data-channel="${video.camera?.channel || ""}" 
          data-description="${video.camera?.description || ""}" 
          data-camera-url="${video.camera?.url || ""}" 
          data-nvr-id="${video.nvr?.id || ""}" 
          data-nvr-area="${video.nvr?.area_name || ""}" 
          data-nvr-url="${video.nvr?.url || ""}">
        </video>
  
        <span class="material-icons play-icon" onclick="openPreview(this)">play_circle</span>
  
        <div class="card-footer text-start">
          <p><strong>Channel:</strong> ${video.camera?.channel || "N/A"}</p>
          <p><strong>Description:</strong> ${
            video.camera?.description || "N/A"
          }</p>
          <strong>Time:</strong> <span class="video-date">${
            video.time
          }</span><br>
          <strong>Duration:</strong> <span class="video-duration">${
            video.duration
          }</span><br>
          <strong>Size:</strong> <span class="video-size">${
            video.size
          }</span><br>
          <a href="${
            video.src
          }" download class="btn btn-primary mt-2 me-2">Download</a>
          <button class="btn btn-danger mt-2" onclick="deleteRecording(this)">Delete</button>
        </div>
      </div>
    </div>
  `;
  });

  recordingItem.innerHTML = `
    <div class="card">
      <div class="card-header">
        <h3>${recordingDay.date}</h3>
      </div>
      <div class="container-fluid p-2">
        <div class="g-2 row">
          ${videosHTML}
        </div>
      </div>
    </div>
  `;

  return recordingItem;
}

function createLoadingIndicator() {
  const loadingElement = document.createElement("div");
  loadingElement.id = "loadingMoreRecordings";
  loadingElement.className = "text-center my-4";
  loadingElement.innerHTML = `
      <div class="d-flex justify-content-center align-items-center flex-column" style="height: 80vh;">
        <div class="text-primary spinner-border" role="status" >
        <span class="visually-hidden">Loading...</span>
      </div>
      <p>Loading more recordings...</p>
      </div>
  `;
  return loadingElement;
}

async function loadRecordings() {
  if (isLoading || !hasMoreRecordings) return;

  isLoading = true;
  recordingsContainer.appendChild(createLoadingIndicator());

  try {
    const result = await fetchRecordings(currentPage, RECORDINGS_PER_LOAD);
    document.getElementById("loadingMoreRecordings")?.remove();

    if (result.recordings.length === 0 && currentPage === 1) {
      const noData = document.createElement("div");
      noData.className =
        "text-center text-muted my-3 d-flex align-items-center justify-content-center";
      noData.textContent = "No recordings found for the selected filters.";
      noData.style.height = "80vh";
      recordingsContainer.appendChild(noData);
      hasMoreRecordings = false;
      return;
    }

    result.recordings.forEach((recordingDay) => {
      const recordingElement = createRecordingDateElement(recordingDay);
      recordingsContainer.appendChild(recordingElement);
    });

    currentPage++;
    hasMoreRecordings = result.hasMore;

    if (!hasMoreRecordings) {
      const endMsg = document.createElement("div");
      endMsg.className = "text-center text-muted my-3";
      endMsg.textContent = "No more recordings.";
      recordingsContainer.appendChild(endMsg);
    }
  } catch (error) {
    console.error("Error loading recordings:", error);
    document.getElementById("loadingMoreRecordings")?.remove();
    const errorMsg = document.createElement("div");
    errorMsg.className = "alert alert-danger text-center my-4";
    errorMsg.textContent = "Failed to load recordings. Please try again.";
    recordingsContainer.appendChild(errorMsg);
  } finally {
    isLoading = false;
  }
}

function handleScroll() {
  if (isLoading || !hasMoreRecordings) return;
  const scrollPos = window.scrollY + window.innerHeight;
  const docHeight = document.documentElement.scrollHeight;
  if (scrollPos >= docHeight - 200) loadRecordings();
}

function initRecordingsTimeline() {
  loadRecordings();
  window.addEventListener("scroll", handleScroll);
  console.log("Recordings timeline initialized");
}

// Filtering
function applyFilters() {
  recordingsContainer.innerHTML = "";
  currentPage = 1;
  hasMoreRecordings = true;
  loadRecordings();
}

function resetFilters() {
  document.getElementById("nvrSelect").value = "all";
  document.getElementById("cameraSelect").innerHTML =
    '<option value="all">All Cameras</option>';
  document.getElementById("cameraSelect").value = "all";
  document.getElementById("startDate").value = "";
  document.getElementById("endDate").value = "";
  recordingsContainer.innerHTML = "";
  currentPage = 1;
  hasMoreRecordings = true;
  loadRecordings();
}

function openPreview(iconElement) {
  const video = iconElement.previousElementSibling; // The <video> element before the icon

  if (!video) {
    console.error("Video element not found");
    return;
  }

  // Set video src and load
  const previewVideo = document.getElementById("previewVideo");
  previewVideo.src = video.src;
  previewVideo.load();

  // Set metadata
  document.getElementById("videoSize").textContent =
    video.dataset.size || "N/A";
  document.getElementById("videoDuration").textContent =
    video.dataset.duration || "N/A";
  document.getElementById("videoDate").textContent =
    video.dataset.date || "N/A";
  document.getElementById("videoChannel").textContent =
    video.dataset.channel || "N/A";
  document.getElementById("videoDescription").textContent =
    video.dataset.description || "N/A";

  const cameraUrl = video.dataset.cameraUrl || "#";
  document.getElementById("videoCameraUrl").textContent = cameraUrl;
  document.getElementById("videoCameraUrlLink").href = cameraUrl;

  document.getElementById("videoNvrArea").textContent =
    video.dataset.nvrArea || "N/A";

  const nvrUrl = video.dataset.nvrUrl || "#";
  document.getElementById("videoNvrUrl").textContent = nvrUrl;
  document.getElementById("videoNvrUrlLink").href = nvrUrl;

  // Show modal
  const modal = new bootstrap.Modal(
    document.getElementById("videoPreviewModal")
  );
  modal.show();
}

async function deleteRecording(button) {
  const video = button.closest(".card").querySelector("video");
  const recordingId = video.dataset.id;

  if (!recordingId) {
    console.error("Recording ID not found");
    return;
  }

  if (!confirm("Are you sure you want to delete this recording?")) return;

  try {
    const res = await fetch(`/api/recordings/${recordingId}`, {
      method: "DELETE",
    });

    const data = await res.json();
    if (res.ok) {
      button.closest(".col-4").remove();
      alert("Recording deleted successfully.");
    } else {
      alert(data.message || "Failed to delete recording.");
    }
  } catch (err) {
    console.error("Error deleting recording:", err);
    alert("Error deleting recording.");
  }
}
