document.addEventListener("DOMContentLoaded", function () {
  fetchNVRList();
});

document.addEventListener("DOMContentLoaded", function () {
  const camSocket = io("/cameras");

  camSocket.on("connect", () => {
    console.log("✅ Connected to camera status stream");
  });

  // WebSocket listener for camera status update
  camSocket.on("camera_status", (data) => {
    const { camera_id, status } = data;
    const badge = document.getElementById(`camera_list_status_${camera_id}`);
    // if (!badge) return;


    // Update badge based on the received status
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
});

// Function to fetch NVR list and auto-select the first one
function fetchNVRList(selectedNVRId = null) {
  fetch("/admin/nvr/list")
    .then((response) => response.json())
    .then((data) => {
      let selectElement = document.getElementById("select-nvr-list");
      selectElement.innerHTML =
        "<option disabled selected value='none'>Select NVR</option>"; // Reset options

      if (data.length === 0) {
        document.getElementById("for-not-selected-nvr").style.display = "flex";
        document.getElementById("manage-camera-area").style.display = "none";
        return;
      } else {
        document.getElementById("for-not-selected-nvr").style.display = "none";
        document.getElementById("manage-camera-area").style.display = "block";
      }

      let firstNVRId = selectedNVRId || data[0].id; // Select first or newly added NVR
      data.forEach((nvr) => {
        let option = document.createElement("option");
        option.value = nvr.id;
        option.textContent = nvr.area_name;
        selectElement.appendChild(option);
      });

      // Set selected NVR and load cameras
      selectElement.value = firstNVRId;
      fetchCameras(firstNVRId);
    })
    .catch((error) => console.error("Error fetching NVR list:", error));
}

// Handle NVR selection change
document
  .getElementById("select-nvr-list")
  .addEventListener("change", function () {
    let selectedNVRId = this.value;
    if (!selectedNVRId) return;
    document.getElementById("for-not-selected-nvr").style.display = "none";
    document.getElementById("manage-camera-area").style.display = "block";
    fetchCameras(selectedNVRId);
  });

function fetchCameras(nvrId) {
  fetch(`/admin/camera/list/${nvrId}`)
    .then((response) => response.json())
    .then((data) => {
      let cameraTable = $("#mytable").DataTable();
      cameraTable.clear().draw(); // Clear table before updating

      if (data.message) {
        // console.warn(data.message);
        return;
      }

      // Populate table with cameras
      data.forEach((camera, index) => {
        cameraTable.row
          .add([
            index + 1, // Sr.No
            camera.channel, // Camera ID
            camera.description,
            camera.url, // Channel
            `<span class='badge text-bg-warning' id='camera_list_status_${camera.id}'>Connecting...</span>`, // Status
            `<button class="btn btn-sm update-button" onclick="showEditCameraModel(${camera.id})" data-bs-toggle="modal" data-bs-target="#staticBackdropCamera">Edit</button>
              <button class="btn btn-sm delete-button" onclick="deleteCamera(${camera.id})">Delete</button>`, // Action
          ])
          .draw(false);
      });
    })
    .catch((error) => console.error("Error fetching cameras:", error));
}

// Handle NVR selection change
document
  .getElementById("select-nvr-list")
  .addEventListener("change", function () {
    let selectedNVRId = this.value;
    if (!selectedNVRId) return;
    document.getElementById("for-not-selected-nvr").style.display = "none";
    document.getElementById("manage-camera-area").style.display = "block";
    fetchCameras(selectedNVRId);
  });

// Add new NVR and update the list
document
  .getElementById("add-nvr-form")
  .addEventListener("submit", function (event) {
    event.preventDefault();

    showLoader();
    let areaName = document.getElementById("nvr-area-name").value;
    let url = document.getElementById("nvr-url").value;
    let id = document.getElementById("nvr-id").value;
    if (!areaName || !url) {
      hideLoader();
      showToast("warning", "Please fill in both Area Name and URL.");
      return;
    }

    if (id === "") {
      fetch("/admin/nvr/addNVR", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ area_name: areaName, url: url }),
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.status) {
            document.getElementById("add-nvr-form").reset(); // Clear form
            document.getElementById("add-nvr-close-btn").click();
            fetchNVRList(data.id); // Fetch updated list and auto-select the new NVR
            hideLoader();
          } else {
            hideLoader();
            showToast("danger", "Error: " + data.message);
          }
        })
        .catch((error) => {
          hideLoader();
          showToast("danger", "Error: " + data.message);
        });
    } else {
      fetch(`/admin/nvr/${id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ area_name: areaName, url: url }),
      })
        .then((response) => response.json())
        .then((data) => {
          if (data.status) {
            document.getElementById("add-nvr-form").reset(); // Clear form
            document.getElementById("add-nvr-close-btn").click();
            document.getElementById("nvr-model-title").innerHTML = "Add NVR";
            document.getElementById("nvr-model-submit-btn").innerHTML =
              "Add NVR";
            fetchNVRList(data.id); // Fetch updated list and auto-select the new NVR
            hideLoader();
          } else {
            hideLoader();
            showToast("danger", "Error: " + data.message);
          }
        })
        .catch((error) => {
          hideLoader();
          showToast("danger", "Error: " + data.message);
        });
    }
  });

// Show "Add Camera" modal with selected NVR details
function showAddCameraModel() {
  let nvrId = document.getElementById("select-nvr-list").value;
  fetch(`/admin/nvr/${nvrId}`)
    .then((response) => response.json())
    .then((data) => {
      document.getElementById(
        "add-camera-nvr-url"
      ).innerHTML = `rtsp://${data.url}`;
      document.getElementById("add-camera-nvr-area-name").value =
        data.area_name;
      document.getElementById("add-camera-nvr-id").value = data.id;
    })
    .catch((error) => console.error("Error fetching NVR details:", error));
}

document
  .getElementById("add-camera-form")
  .addEventListener("submit", function (event) {
    event.preventDefault();
    showLoader();

    let cameraId = document.getElementById("camera-id").value;
    let nvr_id = document.getElementById("add-camera-nvr-id").value;
    let nvr_url = document.getElementById("add-camera-nvr-url").innerHTML;
    let channel_url = document.getElementById("add-camera-further-url").value;
    let camera_channel = document.getElementById("add-camera-id").value;
    let camera_description = document.getElementById(
      "add-camera-description"
    ).value;
    let final_camera_url = nvr_url + channel_url;
    if (!camera_channel || !channel_url || !camera_description) {
      hideLoader();
      showToast("warning", "Please fill in all camera fields.");
      return;
    }

    const payload = {
      url: final_camera_url,
      nvr_id: nvr_id,
      description: camera_description,
      channel: camera_channel,
      channel_url: channel_url,
    };

    // Determine whether to POST (add) or PUT (update)
    let fetchUrl = "";
    let fetchMethod = "";
    console.log(cameraId);
    if (cameraId === "") {
      fetchUrl = "/admin/camera/addCamera";
      fetchMethod = "POST";
    } else {
      fetchUrl = `/admin/camera/${cameraId}`;
      fetchMethod = "PUT";
    }

    fetch(fetchUrl, {
      method: fetchMethod,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.status || data.message) {
          hideLoader();
          document.getElementById("add-camera-close-btn").click();
          fetchCameras(nvr_id); // Refresh camera list
          showToast("success", "Camera is added successfully.");
        } else {
          hideLoader();
          showToast("danger", "Error: " + (data.message || data.error));
        }
      })
      .catch((error) => {
        hideLoader();
        console.error("Error saving camera:", error);
      });
  });

// Initialize DataTable on document ready
$(document).ready(function () {
  $("#mytable").DataTable({
    autoWidth: false,
    pageLength: 15,
    columns: [
      { title: "Sr.No", width: "5%" }, // Sr.No
      { title: "Channel / Camera ID", width: "10%" }, // Camera ID
      { title: "Description", width: "35%" }, // Channel
      { title: "url", width: "15%" }, // Status
      { title: "status", width: "5%" }, // Status
      { title: "Action", width: "20%" }, // Action
    ],
  });
});

// Edit NVR handler
function editNvr() {
  let currentNVRId = document.getElementById("select-nvr-list").value;
  if (currentNVRId === "none") {
    showToast("warning", "Please select an NVR to edit.");
    return;
  }

  fetch(`/admin/nvr/${currentNVRId}`)
    .then((response) => response.json())
    .then((data) => {
      document.getElementById("nvr-url").value = `${data.url}`;
      document.getElementById("nvr-area-name").value = data.area_name;
      document.getElementById("nvr-id").value = data.id;
    })
    .catch((error) => console.error("Error fetching NVR details:", error));
  document.getElementById("nvr-model-title").innerHTML = "Edit NVR";
  document.getElementById("nvr-model-submit-btn").innerHTML = "Edit NVR";
}

function resetNVRForm() {
  document.getElementById("add-nvr-form").reset(); // Clear form
  document.getElementById("nvr-model-title").innerHTML = "Add NVR";
  document.getElementById("nvr-model-submit-btn").innerHTML = "Add NVR";
}

// Dummy function for viewing camera details
function showEditCameraModel(cameraId) {
  let nvrId = document.getElementById("select-nvr-list").value;
  fetch(`/admin/nvr/${nvrId}`)
    .then((response) => response.json())
    .then((data) => {
      document.getElementById(
        "add-camera-nvr-url"
      ).innerHTML = `rtsp://${data.url}`;
      document.getElementById("add-camera-nvr-area-name").value =
        data.area_name;
      document.getElementById("add-camera-nvr-id").value = data.id;
    })
    .catch((error) => console.error("Error fetching NVR details:", error));

  fetch(`/admin/camera/${cameraId}`)
    .then((response) => response.json())
    .then((data) => {
      let camera = data[0];
      document.getElementById("camera-id").value = camera.id;
      document.getElementById("add-camera-id").value = camera.channel;
      document.getElementById("add-camera-further-url").value =
        camera.channel_url;
      document.getElementById("add-camera-description").value =
        camera.description;
    })
    .catch((error) => console.error("Error fetching NVR details:", error));
  document.getElementById("cam-model-title").innerHTML = "Edit Camera";
  document.getElementById("camera-model-submit-btn").innerHTML = "Edit Camera";
}

function resetNVRForm() {
  document.getElementById("add-camera-form").reset(); // Clear form
  document.getElementById("camera-model-title").innerHTML = "Add Camera";
  document.getElementById("camera-model-submit-btn").innerHTML = "Add Camera";
}

function resetCameraForm() {
  document.getElementById("add-camera-form").reset();
  document.getElementById("camera-id").value = "";
  document.getElementById("cam-model-title").innerHTML = "Add Camera";
  document.getElementById("camera-model-submit-btn").innerHTML = "Add Camera";
}

function deleteCamera(cameraId) {
  if (!confirm("Are you sure you want to delete this camera?")) return;

  fetch(`/admin/camera/${cameraId}`, {
    method: "DELETE",
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.message) {
        showToast("success", "Camera deleted successfully.");
        let nvr_id = document.getElementById("select-nvr-list").value;
        fetchCameras(nvr_id); // Refresh camera list
      } else {
        showToast(
          "danger",
          "Error deleting camera: " + (data.error || "Unknown error")
        );
      }
    })
    .catch((error) => console.error("Error deleting camera:", error));
}

function deleteNvr() {
  const select = document.getElementById("select-nvr-list");
  const selectedValue = select.value;

  if (selectedValue === "none") {
    showToast("warning", "Please select an NVR to delete.");
    return;
  }

  if (
    !confirm(
      "Are you sure you want to delete this NVR(Cameras and recordings related to this nvr will be deleted)?"
    )
  )
    return;

  fetch(`/admin/nvr/${selectedValue}`, {
    method: "DELETE",
    headers: {
      "Content-Type": "application/json",
    },
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.status) {
        showToast("success", "NVR deleted successfully.");
        location.reload(); // or update the UI accordingly
      } else {
        showToast("danger", "Error: " + data.error);
      }
    })
    .catch((error) => {
      console.error("Error deleting NVR:", error);
      showToast("danger", "Something went wrong!");
    });
}

function showLoader() {
  console.log("Was called !");
  document.getElementById("global-loader").style.display = "flex";
}

function hideLoader() {
  document.getElementById("global-loader").style.display = "none";
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
  }, 3000);
}
