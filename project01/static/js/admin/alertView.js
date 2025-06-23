const rightColumn = document.getElementById("rightColumn");
const surroundingFeeds = document.querySelectorAll(".resizes-with-main");

document.addEventListener("DOMContentLoaded", function () {
  const closeBtn = document.getElementById("close-camera-list");
  const expandBtn = document.getElementById("expand-camera-list");
  const cameraList = document.querySelector(".camera-list");
  const cameraView = document.querySelector(".camera-view");

  closeBtn.addEventListener("click", () => {
    cameraList.classList.add("collapsed");
    cameraView.classList.add("expanded");
    expandBtn.style.display = "block";

    document.querySelectorAll(".camera-feed").forEach((feed) => {
      const heightPx = parseFloat(window.getComputedStyle(feed).height);
      const currentVh = (heightPx / window.innerHeight) * 100;
      const newVh = currentVh * 1.15;
      feed.style.height = `${newVh}vh`;
    });
  });

  expandBtn.addEventListener("click", () => {
    cameraList.classList.remove("collapsed");
    cameraView.classList.remove("expanded");
    expandBtn.style.display = "none";

    document.querySelectorAll(".camera-feed").forEach((feed) => {
      const heightPx = parseFloat(window.getComputedStyle(feed).height);
      const currentVh = (heightPx / window.innerHeight) * 100;
      const newVh = currentVh / 1.15;
      feed.style.height = `${newVh}vh`;
    });
  });

  fetchInitialLogs();
  const mainFeedImg = document.querySelector("#mainCameraFeed img");
  const right1Container = document.getElementById("rightCamera1");
  const right2Container = document.getElementById("rightCamera2");
  const bottomCamContainer = document.getElementById("bottomCameras");
  const cameraListContainer = document.getElementById("cameraListContainer");

  let currentMainCameraId = null;
  loadFrameEnhancerStatus();
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

  fetch("/admin/camera/list")
    .then((response) => response.json())
    .then((cameras) => {
      const maxSlots = 9;

      // Store all static img elements: feed1 → feed9
      feedSlots = Array.from({ length: maxSlots }, (_, i) => {
        return document.querySelector(`#feed${i + 1} img`);
      });

      feedCameraIds = [];

      if (cameras.length === 0) {
        const mainFeedWrapper = document.getElementById("feed1");
        mainFeedWrapper.innerHTML = `<div class="text-center w-100 p-4"><strong>No cameras added.</strong></div>`;
        return;
      }

      // Fill only the cameras available
      for (let i = 0; i < maxSlots; i++) {
        const img = feedSlots[i];
        const cam = cameras[i];

        if (cam) {
          img.alt = `Camera ${cam.id}`;
          img.setAttribute("data-cam-id", cam.id);
          img.setAttribute("id", `camera_feed_${cam.id}`);
          img.style.display = "block";
          img.parentElement.style.background = "";
          feedCameraIds.push(cam.id);
        } else {
          // Empty slot
          img.style.display = "none";
          img.removeAttribute("data-cam-id");
          img.parentElement.innerHTML = `<div class="text-white bg-dark w-100 h-100 d-flex align-items-center justify-content-center fw-bold">No Camera Added</div>`;
        }
      }

      // Track the main feed camera ID
      currentMainCameraId = feedCameraIds[0];

      // 👉 Render side camera list
      cameraListContainer.innerHTML = "";
      cameras.forEach((camera) => {
        const cameraListItem = document.createElement("li");
        cameraListItem.classList.add("list-group-item", "p-2", "w-100");

        cameraListItem.innerHTML = `
          <div class="d-flex align-items-center w-100">
            <div class="small-camera-feed me-2">
              <img 
                id="camera_list_${camera.id}"
                src="" 
                alt="Camera ${camera.id}" 
                style="width: 100%; height: 100%;">
            </div>
            <div>
              <div class="p-1 d-flex align-items-top flex-column">
                <strong style="font-size:0.75rem">${camera.channel}</strong>
                <p><span class="badge text-bg-warning" id="camera_list_status_${camera.id}">Connecting...</span></p>
              </div>
            </div>
          </div>
        `;
        cameraListContainer.appendChild(cameraListItem);
      });
    })
    .catch((error) => console.error("Error fetching cameras:", error));
  // Handle WebSocket for new logs
  const logSocket = io("/logs");

  logSocket.on("connect", () => {
    console.log("✅ Connected to log events");
  });

  logSocket.on("new_log", function (log) {
    const cameraId = log.camera_id;

    // Optional: log UI rendering
    const list = document.getElementById("logList");
    if (list) {
      const currentDateTime = `${log.date} ${log.time}`;
      const dateHeader = document.createElement("li");
      dateHeader.className =
        "list-group-item list-group-item-action list-group-item-dark";
      dateHeader.innerHTML = `<span class="text-dark fw-bolder">${currentDateTime}</span>`;

      const item = document.createElement("li");
      item.className = "list-group-item";
      item.innerHTML = `
      <span class="fw-bolder">Camera Id :</span> <span class="fw-bold">${
        log.camera_id
      }</span>
      <span class="fw-bolder">Class :</span> <span class="fw-bold">${
        log.class
      }</span>
      <span class="fw-bolder">Confidence :</span> <span class="fw-bold">${(
        log.confidence * 100
      ).toFixed(2)}%</span>
      `;
      list.prepend(item);
      list.prepend(dateHeader);
    }
    rotateFeedsWithNewCamera(cameraId);
  });
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

const recordingSocket = io("/recordings");
// 🔁 Update to your host if needed

recordingSocket.on("connect", () => {
  console.log("✅ Connected to recording events");
});

recordingSocket.on("recording_event", (data) => {
  const { camera_id, status } = data;
  if (status === "started") {
    showToast("warning", `🎥 Camera ${camera_id} started recording...`);
  } else if (status === "stopped") {
    showToast("success", `✅ Camera ${camera_id} recording saved.`);
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

function rotateFeedsWithNewCamera(newCamId) {
  if (feedCameraIds[0] === newCamId) return;

  const existingIndex = feedCameraIds.indexOf(newCamId);
  if (existingIndex !== -1) {
    feedCameraIds.splice(existingIndex, 1);
  }

  // Insert new camera at beginning
  feedCameraIds.unshift(newCamId);
  feedCameraIds = feedCameraIds.slice(0, feedSlots.length); // Trim to max slots

  // Update DOM
  for (let i = 0; i < feedSlots.length; i++) {
    const img = feedSlots[i];
    const camId = feedCameraIds[i];

    if (!img || !img.parentElement) continue;

    const parent = img.parentElement;
    parent.innerHTML = ""; // Clear the parent
    const newImg = document.createElement("img");
    newImg.style.width = "100%";
    newImg.style.height = "100%";

    if (camId) {
      newImg.src = `http://localhost:8080/stream/${camId}`;
      newImg.alt = `Camera ${camId}`;
      newImg.setAttribute("data-cam-id", camId);
      parent.appendChild(newImg);
    } else {
      parent.innerHTML = `
        <div class="text-white bg-dark w-100 h-100 d-flex align-items-center justify-content-center fw-bold">
          No Camera Added
        </div>`;
    }

    // Update slot reference
    feedSlots[i] = newImg;
  }

  currentMainCameraId = feedCameraIds[0];
}

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

camSocket.on("frame", (data) => {
  const { camera_id, image } = data;

  // ✅ Feed Grid
  const imgElement = document.getElementById(`camera_feed_${camera_id}`);
  if (imgElement) {
    imgElement.src = `data:image/jpeg;base64,${image}`;
  }

  // ✅ Camera List Thumbnail (if used)
  const imgListElement = document.getElementById(`camera_list_${camera_id}`);
  if (imgListElement) {
    imgListElement.src = `data:image/jpeg;base64,${image}`;
  }

  // ✅ Live Preview if needed
  // if (camera_id === currentlyPreviewedCameraId) {
  //   const previewImg = document.getElementById("previewImage");
  //   if (previewImg) {
  //     previewImg.src = `data:image/jpeg;base64,${image}`;
  //   }
  // }
});
