function toggleMenu(event, menuId) {
  event.stopPropagation();
  document.querySelectorAll(".dropdown-menu").forEach((menu) => {
    if (menu.id !== menuId) menu.classList.remove("show");
  });
  document.getElementById(menuId).classList.toggle("show");
}
let currentlyPreviewedCameraId = null;

// Close menu if clicked outside
window.onclick = function () {
  document.querySelectorAll(".dropdown-menu").forEach((menu) => {
    menu.classList.remove("show");
  });
};

document.addEventListener("DOMContentLoaded", function () {
  // Fetch recording status first
  let recordingStatus = {};

  fetch("/admin/get_selected_model")
    .then((res) => res.json())
    .then((data) => {
      const selected = data.model_selected;
      const select = document.getElementById("model-select");
      if (select && selected) {
        select.value = selected;
      }
    })
    .catch((err) => console.error("Error fetching selected model:", err));

  fetch("/api/manual_recordings")
    .then((res) => res.json())
    .then((statusData) => {
      recordingStatus = statusData;
    })
    .then(() => {
      // Now fetch all cameras
      fetch("/admin/camera/list") // Adjust the API URL as needed
        .then((response) => response.json())
        .then((cameras) => {
          const cameraContainer = document.getElementById("cameraContainer");
          cameraContainer.innerHTML = "";

          if (cameras.length === 0) {
            cameraContainer.innerHTML = `<div class="text-center w-100 p-4"><strong>No cameras added.</strong></div>`;
          } else {
            cameras.forEach((camera) => {
              const isRecording = recordingStatus[camera.id] === true;

              const cameraDiv = document.createElement("div");
              cameraDiv.classList.add("col-4", "column");

              cameraDiv.innerHTML = `
                <div class="camera-feed" style="position: relative;">
                  <button 
                    id="record-btn-${camera.id}"
                    class="record-button manual-recording-btn ${
                      isRecording ? "blinking" : ""
                    }" 
                    onclick="toggleRecording('${camera.id}')"
                  >
                    <span class="material-icons mt-1">
                      ${isRecording ? "stop_circle" : "radio_button_checked"}
                    </span>
                  </button>

                  <img 
                    src="http://localhost:8080/stream/${camera.id}"
                    alt="Camera ${camera.id}" 
                    id="camera_feed_${camera.id}" 
                    class="camera-image"
                    style="width: 100%; height: 100%; cursor: pointer;">

                  <!-- 👇 Label for Camera ID -->
                  <div class="camera-id-label" id="camera_id_label_${
                    camera.id
                  }">${camera.id}</div>
                </div>
              `;

              cameraDiv
                .querySelector("img")
                .addEventListener("dblclick", () => {
                  currentlyPreviewedCameraId = camera.id;
                  document.getElementById("cameraPreviewModal").style.display =
                    "block";
                });

              cameraContainer.appendChild(cameraDiv);
            });
          }

          // Populate camera list (unchanged)
          const cameraListContainer = document.getElementById(
            "cameraListContainer"
          );
          cameraListContainer.innerHTML = "";

          if (cameras.length === 0) {
            cameraListContainer.innerHTML = `<li class="list-group-item text-center text-muted">No cameras added.</li>`;
          } else {
            cameras.forEach((camera) => {
              const cameraListItem = document.createElement("li");
              cameraListItem.classList.add("list-group-item", "p-1", "w-100");

              cameraListItem.innerHTML = `
                <div class="d-flex align-items-center w-100">
                  <div class="small-camera-feed">
                    <img src="http://localhost:8080/stream/${camera.id}" alt="Camera ${camera.id}" id="camera_list_${camera.id}" style="width: 100%;height: 100%;">
                  </div>
                  <div>
                    <div class="p-1 d-flex align-items-top flex-column">
                      <strong class="p-0"><span class="" style="font-size:0.75rem" title="Channel name">${camera.channel}</span></strong>
                      <p><span class="badge text-bg-warning" id="camera_list_status_${camera.id}">Connecting...</span></p>
                    </div>
                  </div>
                </div>
              `;

              cameraListContainer.appendChild(cameraListItem);
            });
          }
        })
        .catch((error) => console.error("Error fetching cameras:", error));
    })
    .catch((error) => console.error("Error fetching recording status:", error));
  fetchInitialLogs();
  loadFrameEnhancerStatus();
});

document.getElementById("model-select").addEventListener("change", function () {
  const selectedModel = this.value;

  fetch(`/admin/changeAiModel/${selectedModel}`, {
    method: "GET",
  })
    .then((response) => response.json())
    .then((data) => {
      showToast("success", `Mode Changed Sucessfully.`);
    })
    .catch((error) => {
      showToast("dange", `Error while changing mode.(${error})`);
    });
});

function setGrid(columns, buttonElement) {
  console.log(columns);
  const column = document.querySelectorAll(".column");

  // Check if camera list is currently collapsed
  const isCollapsed = document
    .querySelector(".camera-list")
    .classList.contains("collapsed");

  // Define base height values (in vh)
  let baseHeight = 70;
  if (columns === 2) baseHeight = 35;
  else if (columns === 3) baseHeight = 25;
  else if (columns === 4) baseHeight = 20;

  // If collapsed, increase height by 5%
  const finalHeight = isCollapsed ? baseHeight * 1.5 : baseHeight;

  // Apply height
  document.querySelectorAll(".camera-feed").forEach((element) => {
    element.style.height = `${finalHeight}vh`;
  });

  // Update grid buttons' visual state
  document.querySelectorAll(".grid-buttons").forEach((element) => {
    element.className = `btn btn-secondary grid-buttons`;
  });
  buttonElement.className = `btn btn-primary grid-buttons`;

  // Update column width
  column.forEach((feed) => {
    feed.className = `col-${12 / columns} column`;
  });
}

function toggleRecording(cameraId) {
  const button = document.querySelector(`#record-btn-${cameraId}`);
  const icon = button.querySelector("span");

  // Save original icon
  const originalIcon = icon.textContent;

  // Show spinner and disable button
  button.disabled = true;
  icon.innerHTML = `<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>`;

  fetch("/api/manual_recordings", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ camera_id: cameraId }),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.recording) {
        button.classList.add("blinking");
        icon.textContent = "stop_circle";
      } else {
        button.classList.remove("blinking");
        icon.textContent = "radio_button_checked";
      }
      console.log(`Camera ${cameraId} recording: ${data.recording}`);
    })
    .catch((error) => {
      console.error("Error toggling recording:", error);
      alert("Failed to toggle recording.");
      icon.textContent = originalIcon; // fallback to old icon
    })
    .finally(() => {
      button.disabled = false;
    });
}

document.addEventListener("DOMContentLoaded", function () {
  const closeBtn = document.getElementById("close-camera-list");
  const expandBtn = document.getElementById("expand-camera-list");
  const cameraList = document.querySelector(".camera-list");
  const cameraView = document.querySelector(".camera-view");

  closeBtn.addEventListener("click", () => {
    cameraList.classList.add("collapsed");
    cameraView.classList.add("expanded");
    expandBtn.style.display = "flex";

    document.querySelectorAll(".camera-feed").forEach((feed) => {
      const heightStr = window.getComputedStyle(feed).height; // e.g., "150px"
      const heightPx = parseFloat(heightStr); // 150

      const vh = (heightPx / window.innerHeight) * 100;
      const increasedVh = vh * 1.5;

      feed.style.height = `${increasedVh}vh`;
    });
  });

  expandBtn.addEventListener("click", () => {
    cameraList.classList.remove("collapsed");
    cameraView.classList.remove("expanded");
    expandBtn.style.display = "none";

    document.querySelectorAll(".camera-feed").forEach((feed) => {
      const heightStr = window.getComputedStyle(feed).height;
      const heightPx = parseFloat(heightStr);

      const vh = (heightPx / window.innerHeight) * 100;
      const decreasedVh = vh / 1.5;

      feed.style.height = `${decreasedVh}vh`;
    });
  });
});

const socket = io("/recordings");
// 🔁 Update to your host if needed

const toastEl = document.getElementById("recordingToast");
const toastBody = document.getElementById("recordingToastBody");
const bsToast = new bootstrap.Toast(toastEl);

socket.on("connect", () => {
  console.log("✅ Connected to recording events");
});

socket.on("recording_event", (data) => {
  const { camera_id, status } = data;
  if (status === "started") {
    showToast("warning", `Camera ${camera_id} started recording...`);
  } else if (status === "stopped") {
    showToast("success", `Camera ${camera_id} recording saved.`);
  } else if (status === "ModelChanging") {
    showToast("warning", "Please Wait New Models Are Getting Load...");
  } else if (status === "ModelChanged") {
    showToast("success", "New Trained Model Loaded Successfully !");
  }
});

const camSocket = io("/cameras");

camSocket.on("connect", () => {
  console.log("✅ Connected to camera status stream");
});

camSocket.on("camera_status", (data) => {
  const { camera_id, status } = data;
  const badge = document.getElementById(`camera_list_status_${camera_id}`);
  if (!badge) return;

  if (status === "Receiving Frames") {
    badge.classList.remove("text-bg-danger", "text-bg-warning");
    badge.classList.add("text-bg-success");
    badge.innerText = "Online";
  } else if (status === "Reconnecting") {
    badge.classList.remove("text-bg-success", "text-bg-danger");
    badge.classList.add("text-bg-warning");
    badge.innerText = "Reconnecting...";
  } else {
    badge.classList.remove("text-bg-success", "text-bg-warning");
    badge.classList.add("text-bg-danger");
    badge.innerText = "Disconnected";
  }
});

function showToast(type = "info", message = "This is a toast!") {
  const toastContainer = document.getElementById("toast-container");

  // Create toast element
  const toast = document.createElement("div");
  toast.className = `toast align-items-center text-white bg-${type} border-0 show`;
  toast.setAttribute("role", "alert");
  toast.setAttribute("aria-live", "assertive");
  toast.setAttribute("aria-atomic", "true");

  toast.style.minWidth = "250px";
  toast.style.padding = "10px 15px";

  toast.innerHTML = `
    <div class="d-flex justify-content-between align-items-center">
      <div>${message}</div>
      <button type="button" class="btn-close btn-close-white ms-2 mb-1" onclick="this.parentElement.parentElement.remove()"></button>
    </div>
  `;

  toastContainer.appendChild(toast);

  // Auto remove after 2 seconds
  setTimeout(() => {
    toast.remove();
  }, 2000);
}

function fetchInitialLogs() {
  fetch("/admin/fetchLogs?offset=0&limit=25")
    .then((res) => res.json())
    .then((logs) => {
      const list = document.getElementById("live-log-list");
      list.innerHTML = "";
      logs.reverse().forEach(renderLogEntry);
    });
}

function renderLogEntry(log) {
  const list = document.getElementById("live-log-list");
  const time = log.time;
  const item = document.createElement("li");

  item.className = "list-group-item blink-log";
  item.innerHTML = `
    <span class="fw-bold">${time}</span>
    <span> Camera Id : ${log.camera_id}</span>
    <span> Class : ${log.class}</span>
    <span> Confidence : ${(parseFloat(log.confidence) * 100).toFixed(2)}%</span>
  `;

  list.prepend(item);
  if (list.children.length > 100) list.removeChild(list.lastChild);
  setTimeout(() => item.classList.remove("blink-log"), 1500);
}

const logSocket = io("/logs");
logSocket.on("connect", () => console.log("✅ Connected to log stream"));
logSocket.on("new_log", (log) => renderLogEntry(log));

(function () {
  const panel = document.getElementById("liveLogPanel");
  const handle = document.getElementById("logResizeHandle");
  let isResizing = false;
  let startY, startHeight;

  handle.addEventListener("mousedown", function (e) {
    isResizing = true;
    startY = e.clientY;
    startHeight = parseInt(window.getComputedStyle(panel).height, 10);
    document.body.style.cursor = "row-resize";
    document.addEventListener("mousemove", onMouseMove);
    document.addEventListener("mouseup", onMouseUp);
  });

  function onMouseMove(e) {
    if (!isResizing) return;
    const newHeight = startHeight - (e.clientY - startY);
    panel.style.height =
      Math.max(100, Math.min(window.innerHeight / 2, newHeight)) + "px";
  }

  function onMouseUp() {
    isResizing = false;
    document.body.style.cursor = "";
    document.removeEventListener("mousemove", onMouseMove);
    document.removeEventListener("mouseup", onMouseUp);
  }
})();

document
  .getElementById("toggleLogPanelBtn")
  .addEventListener("click", function () {
    const panel = document.getElementById("liveLogPanel");
    const button = this;

    const isCollapsed = panel.classList.toggle("collapsed");

    // Change button icon
    button.innerHTML = isCollapsed
      ? "keyboard_arrow_up"
      : "keyboard_arrow_down";
  });

const checkbox = document.getElementById("frame_enhancer_switch");

// Listen for the change event
checkbox.addEventListener("change", function () {
  const status = checkbox.checked;
  // Send the request to the Flask route
  fetch(`/admin/changeFrameEnhancer/${status}`, {
    method: "GET", // You can change this to POST if you want
    headers: {
      "Content-Type": "application/json",
    },
  })
    .then((response) => response.json())
    .then((data) => {
      // Handle the response from the Flask server
      showToast("success", data.message); // You can use this to update the UI if needed
    })
    .catch((error) => console.error("Error:", error));
});

function loadFrameEnhancerStatus() {
  fetch("/admin/getFrameEnhancerStatus", {
    method: "GET", // GET request to fetch the current status
    headers: {
      "Content-Type": "application/json",
    },
  })
    .then((response) => response.json())
    .then((data) => {
      // Set the checkbox to the fetched status
      const checkbox = document.getElementById("frame_enhancer_switch");
      checkbox.checked = data.model_selected === "enabled"; // Adjust based on your model response
    })
    .catch((error) => console.error("Error:", error));
}

document.getElementById("closePreviewBtn").addEventListener("click", () => {
  const modal = document.getElementById("cameraPreviewModal");
  const previewImage = document.getElementById("previewImage");
  previewImage.src = "";
  modal.style.display = "none";
  currentlyPreviewedCameraId = null;
});

camSocket.on("frame", (data) => {
  const { camera_id, image } = data;

  // Thumbnail Update
  const imgElement = document.getElementById(`camera_feed_${camera_id}`);
  const imgListElement = document.getElementById(`camera_list_${camera_id}`);
  if (imgElement) {
    imgElement.src = `data:image/jpeg;base64,${image}`;
    imgListElement.src = `data:image/jpeg;base64,${image}`;
  }

  // Preview Update
  if (camera_id === currentlyPreviewedCameraId) {
    const previewImg = document.getElementById("previewImage");
    if (previewImg) {
      previewImg.src = `data:image/jpeg;base64,${image}`;
    }
  }
});
