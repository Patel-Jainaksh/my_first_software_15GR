let socket = io();

// Listen for extraction complete event
socket.on("extraction_complete", (data) => {
  console.log("Extraction complete:", data);
  $("#mytable").DataTable().ajax.reload(); // Refresh the table
});

$(document).ready(function () {
  $("#mytable").DataTable({
    ajax: {
      url: "/api/manual_recordings",
      dataSrc: "",
    },
    columns: [
      { data: "sr_no" },
      { data: "file_path" },
      { data: "duration" },
      { data: "channel" },
      {
        data: null,
        render: function (data, type, row) {
          if (row.extract_status === "in_progress") {
            return `<button class="btn btn-sm btn-outline-secondary" disabled>Extracting...</button>`;
          }
          if (row.extract_frame || row.extract_status === "completed") {
            return `<a href="/annotate/${row.id}" class="btn btn-sm btn-primary">Start Annotation</a>`;
          }
          return `<button class="btn btn-sm btn-outline-success" onclick="extractFrame(${row.id}, this)">Extract</button>`;
        },
      },
      {
        data: null,
        render: function (data, type, row) {
          return `<button class="btn btn-sm btn-outline-danger" onclick="deleteRecording(${row.id})">Delete</button>`;
        },
      },
    ],
  });
});

function deleteRecording(id) {
  if (!confirm("Are you sure you want to delete this recording?")) return;

  $.ajax({
    url: `/api/manual_recordings/${id}`,
    type: "DELETE",
    success: function (response) {
      alert(response.message);
      $("#mytable").DataTable().ajax.reload(); // Refresh the table after deletion
    },
    error: function (xhr) {
      alert(xhr.responseJSON?.message || "Failed to delete recording.");
    },
  });
}

function extractFrame(id, btn) {
  btn.disabled = true;
  btn.innerText = "Extracting...";
  $.post(`/api/manual_recordings/${id}/extract`)
    .done(() => console.log("Extraction started"))
    .fail((err) => alert(err.responseJSON.message));
}

document.addEventListener("DOMContentLoaded", function () {
  const videoInput = document.getElementById("videoInput");

  if (videoInput) {
    videoInput.addEventListener("change", function () {
      const file = videoInput.files[0];
      if (!file) return;

      const formData = new FormData();
      formData.append("video", file);

      fetch("/upload_video", {
        method: "POST",
        body: formData
      })
        .then((res) => res.json())
        .then((data) => {
          alert(data.message || "Upload successful!");
          $("#mytable").DataTable().ajax.reload(); // Reload only the table
        })
        .catch((err) => {
          alert("Upload failed.");
          console.error(err);
        });
    });
  }
});
