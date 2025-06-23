let offset = 0;
const limit = 50;
let loading = false;
const list = document.getElementById("log-items");

// Fetch NVRs and their cameras
async function fetchNVRsAndCameras() {
  const nvrSelect = document.getElementById("nvr-select");
  const cameraSelect = document.getElementById("camera-select");

  const nvrs = await fetch("/admin/getNVRs").then((res) => res.json());
  nvrs.forEach((nvr) => {
    const opt = document.createElement("option");
    opt.value = nvr.id;
    opt.textContent = nvr.area_name;
    nvrSelect.appendChild(opt);
  });

  nvrSelect.addEventListener("change", async () => {
    const nvrId = nvrSelect.value;
    cameraSelect.innerHTML = '<option value="">Select Camera</option>';
    if (!nvrId) return;

    const cams = await fetch(`/admin/getCamerasByNVR?nvr_id=${nvrId}`).then(
      (r) => r.json()
    );
    cams.forEach((cam) => {
      const opt = document.createElement("option");
      opt.value = cam.id;
      opt.textContent = cam.desc;
      cameraSelect.appendChild(opt);
    });
  });
}

// Format date input to dd-mm-yyyy
function formatToDDMMYYYY(dateStr) {
  if (!dateStr) return "";
  const [year, month, day] = dateStr.split("-");
  return `${day}-${month}-${year}`;
}

// Load logs with optional reset
async function loadLogs(reset = false) {
  if (loading) return;
  loading = true;

  if (reset) {
    offset = 0;
    list.innerHTML = "";
  }

  const camId = document.getElementById("camera-select").value;
  const rawStartDate = document.getElementById("start-date").value;
  const rawEndDate = document.getElementById("end-date").value;
  const startDate = formatToDDMMYYYY(rawStartDate);
  const endDate = formatToDDMMYYYY(rawEndDate);

  const params = new URLSearchParams({ offset, limit });
  if (camId) params.append("camera_id", camId);
  if (startDate) params.append("start_date", startDate);
  if (endDate) params.append("end_date", endDate);

  const response = await fetch(`/admin/fetchLogs?${params}`);
  const data = await response.json();

  if (data.length === 0 && reset) {
    const noLogs = document.createElement("li");
    noLogs.className = "list-group-item text-muted text-center";
    noLogs.innerHTML = "No logs found for the selected filters.";
    list.appendChild(noLogs);
    loading = false;
    return;
  }

  data.forEach((log) => {
    const item = document.createElement("li");
    item.className = "list-group-item";
    item.innerHTML = `
      <span class="fw-bolder">${log.date} ${log.time}</span>
      <span class="fw-bolder"> | Camera Id:</span> <span class="fw-bold">${
        log.camera_id
      }</span>
      <span class="fw-bolder"> | Class:</span> <span class="fw-bold">${
        log.class
      }</span>
      <span class="fw-bolder"> | Confidence:</span> 
      <span class="fw-bold">${(parseFloat(log.confidence) * 100).toFixed(
        2
      )}%</span>
    `;
    list.appendChild(item);
  });

  offset += limit;
  loading = false;
}

// Reload logs when filters are changed
function reloadLogs() {
  loadLogs(true);
}

// Initial setup
fetchNVRsAndCameras();
loadLogs();

// Infinite scroll
window.addEventListener("scroll", () => {
  if (window.innerHeight + window.scrollY >= document.body.offsetHeight - 200) {
    loadLogs();
  }
});

// Socket logs (real-time updates)
const socket = io("/logs");
socket.on("new_log", function (log) {
  const selectedCam = document.getElementById("camera-select").value;
  if (selectedCam && log.camera_id !== selectedCam) return;

  const item = document.createElement("li");
  item.className = "list-group-item";
  item.innerHTML = `
    <span class="fw-bolder">${log.date} ${log.time}</span>
    <span class="fw-bolder"> | Camera Id:</span> <span class="fw-bold">${
      log.camera_id
    }</span>
    <span class="fw-bolder"> | Class:</span> <span class="fw-bold">${
      log.class
    }</span>
    <span class="fw-bolder"> | Confidence:</span> 
    <span class="fw-bold">${(parseFloat(log.confidence) * 100).toFixed(
      2
    )}%</span>
  `;
  list.prepend(item);
});

// Reset filter button
function resetFilters() {
  document.getElementById("nvr-select").selectedIndex = 0;
  document.getElementById("camera-select").innerHTML =
    '<option value="">Select Camera</option>';
  document.getElementById("start-date").value = "";
  document.getElementById("end-date").value = "";

  offset = 0;
  list.innerHTML = "";
  loadLogs(true);
}

// Delete logs by date
async function deleteLogsByDate(date) {
  if (!confirm(`Are you sure you want to delete all logs for ${date}?`)) return;

  try {
    const res = await fetch(`/admin/deleteLogsByDate?date=${date}`, {
      method: "DELETE",
    });
    const data = await res.json();

    if (res.ok) {
      alert(data.message);
      reloadLogs();
    } else {
      alert(data.message || "Failed to delete logs.");
    }
  } catch (err) {
    console.error("Error deleting logs:", err);
    alert("Error deleting logs.");
  }
}

