let currentFrameIndex = 0;
let frames = [];
let annotations = {}; // frameId -> array of {x, y, w, h, label}

let startX,
  startY,
  isDrawing = false;
let canvas, ctx;

function loadFrames() {
  fetch(`/api/frames/${RECORDING_ID}`)
    .then((res) => res.json())
    .then((data) => {
      frames = data.sort((a, b) =>
        a.frame_path.localeCompare(b.frame_path, undefined, { numeric: true })
      );
      buildFrameList();
      showFrame(currentFrameIndex);
    });
}

function buildFrameList() {
  const list = document.getElementById("frameListItems");
  list.innerHTML = "";

  frames.forEach((frame, index) => {
    const li = document.createElement("li");
    li.classList.add("list-group-item", "text-truncate", "p-1", "border-end-0");
    li.innerText = frame.frame_path.split("/").pop();
    li.onclick = () => {
      currentFrameIndex = index;
      showFrame(index);
    };
    list.appendChild(li);
  });
}

function showFrame(index) {
  canvas = document.getElementById("mainCanvas");
  ctx = canvas.getContext("2d");
  const frame = frames[index];
  const img = new Image();

  document.querySelectorAll("#frameListItems li").forEach((el, idx) => {
    el.classList.toggle("active", idx === index);
  });

  img.onload = () => {
    const maxW = window.innerWidth * 0.82;
    const maxH = window.innerHeight * 0.75;
    const scale = Math.min(maxW / img.width, maxH / img.height);
    const displayWidth = img.width * scale;
    const displayHeight = img.height * scale;

    canvas.width = img.width;
    canvas.height = img.height;

    canvas.style.width = `${displayWidth}px`;
    canvas.style.height = `${displayHeight}px`;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0);
    drawBoxes();
  };

  img.src = `http://localhost:8082${frame.frame_path}`;
  document.getElementById("frame-name").innerText = frame.frame_path
    .split("/")
    .pop();

  canvas.onmousedown = startDraw;
  canvas.onmouseup = endDraw;
  canvas.onmousemove = drawing;

  fetch(`/api/annotation/${frame.id}`)
    .then((res) => res.json())
    .then((data) => {
      annotations[frame.id] = data || [];
      redrawCanvas();
      updateAnnotationList();
    });
}

function getScaledMousePos(e) {
  const rect = canvas.getBoundingClientRect();
  const scaleX = canvas.width / rect.width;
  const scaleY = canvas.height / rect.height;
  return {
    x: (e.clientX - rect.left) * scaleX,
    y: (e.clientY - rect.top) * scaleY,
  };
}

function startDraw(e) {
  const pos = getScaledMousePos(e);
  startX = pos.x;
  startY = pos.y;
  isDrawing = true;
}

let tempBox = null;

function drawing(e) {
  if (!isDrawing) return;
  const pos = getScaledMousePos(e);
  const w = pos.x - startX;
  const h = pos.y - startY;
  tempBox = { x: startX, y: startY, w, h };
  redrawCanvas();
}

function endDraw() {
  isDrawing = false;
}

function redrawCanvas() {
  const img = new Image();
  img.src = `http://localhost:8082/${frames[currentFrameIndex].frame_path}`;
  img.onload = () => {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.drawImage(img, 0, 0);
    drawBoxes();
    if (tempBox) {
      ctx.strokeStyle = "blue";
      ctx.lineWidth = 2;
      ctx.strokeRect(tempBox.x, tempBox.y, tempBox.w, tempBox.h);
    }
  };
}

function drawBoxes() {
  const frameId = frames[currentFrameIndex].id;
  if (!annotations[frameId]) return;

  annotations[frameId].forEach((box) => {
    ctx.strokeStyle = "red";
    ctx.lineWidth = 2;
    ctx.strokeRect(box.x, box.y, box.w, box.h);
    ctx.fillStyle = "red";
    ctx.font = "14px sans-serif";
    const labelText =
      box.score !== undefined
        ? `${box.label} (${(box.score * 100).toFixed(1)}%)`
        : box.label;
    ctx.fillText(labelText, box.x + 4, box.y - 5);
  });
}

function navigateFrame(dir) {
  const newIndex = currentFrameIndex + dir;
  if (newIndex >= 0 && newIndex < frames.length) {
    currentFrameIndex = newIndex;
    showFrame(newIndex);
  }
}

function saveAnnotations() {
  const frameId = frames[currentFrameIndex].id;
  const boxes = annotations[frameId] || [];
  const payload = [{ frame_id: parseInt(frameId), boxes }];

  fetch("/api/save_annotations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  })
    .then((res) => res.json())
    .then(() => {
      const toast = new bootstrap.Toast(document.getElementById("saveToast"));
      toast.show();
      setTimeout(() => toast.hide(), 3000);
    });
}

function jumpToNextUnannotated() {
  for (let i = currentFrameIndex + 1; i < frames.length; i++) {
    const frameId = frames[i].id;
    if (!annotations[frameId] || annotations[frameId].length === 0) {
      currentFrameIndex = i;
      showFrame(i);
      return;
    }
  }
  alert("🎉 All frames are annotated!");
}

function addAnnotation() {
  if (!tempBox) return;
  const label = document.getElementById("labelSelect").value;
  const frameId = frames[currentFrameIndex].id;
  if (!annotations[frameId]) annotations[frameId] = [];

  const x = Math.min(tempBox.x, tempBox.x + tempBox.w);
  const y = Math.min(tempBox.y, tempBox.y + tempBox.h);
  const w = Math.abs(tempBox.w);
  const h = Math.abs(tempBox.h);

  annotations[frameId].push({ x, y, w, h, label });
  tempBox = null;
  redrawCanvas();
  updateAnnotationList();
}

function updateAnnotationList() {
  const frameId = frames[currentFrameIndex].id;
  const list = document.getElementById("annotationList");
  list.innerHTML = "";

  const frameAnnotations = annotations[frameId] || [];

  if (frameAnnotations.length === 0) {
    const emptyMsg = document.createElement("li");
    emptyMsg.classList.add(
      "list-group-item",
      "text-center",
      "h-100",
      "d-flex",
      "align-items-center",
      "justify-content-center",
      "text-dark",
      "fs-6",
      "fw-bold",
    );
    emptyMsg.innerText = "No Annotations";
    list.appendChild(emptyMsg);
    return;
  }

  frameAnnotations.forEach((box, idx) => {
    const li = document.createElement("li");
    li.classList.add(
      "list-group-item",
      "d-flex",
      "justify-content-between",
      "align-items-center"
    );
    li.innerHTML = `
      <span>
        ${box.label}${
      box.score !== undefined ? ` (${(box.score * 100).toFixed(1)}%)` : ""
    } 
        (${box.x.toFixed(0)},${box.y.toFixed(0)},${box.w.toFixed(
      0
    )}x${box.h.toFixed(0)})
      </span>
      <span class="material-icons text-danger remove-annotation hover-shadow fw-bolder" role="button" onclick="removeAnnotation(${idx})">remove</span>
    `;
    list.appendChild(li);
  });
}

function removeAnnotation(index) {
  const frameId = frames[currentFrameIndex].id;
  if (annotations[frameId]) {
    annotations[frameId].splice(index, 1);
    updateAnnotationList();
    redrawCanvas();
  }
}

function autoAnnotate() {
  const btn = document.getElementById("autoAnnotateBtn");
  btn.disabled = true;
  btn.innerText = "Loading...";

  const frame = frames[currentFrameIndex];
  const confidence =
    parseFloat(document.getElementById("confidenceRange").value) / 100;

  fetch(`/api/auto_annotate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ frame_id: frame.id, confidence }),
  })
    .then((res) => res.json())
    .then((data) => {
      console.log(data.detections);
      annotations[frame.id] = (data.detections || []).map((det) => {
        const x1 = det.xmin;
        const y1 = det.ymin;
        const x2 = det.xmax;
        const y2 = det.ymax;

        return {
          x: x1,
          y: y1,
          w: x2 - x1,
          h: y2 - y1,
          label: det.class, // Use det.label if it exists, otherwise fallback to class
          score: det.confidence || det.score || 0,
        };
      });
      redrawCanvas();
      updateAnnotationList();
    })
    .catch((err) => {
      alert("Auto annotation failed.");
      console.error(err);
    })
    .finally(() => {
      btn.disabled = false;
      btn.innerText = "Auto Annotate";
    });
}

document.addEventListener("keydown", function (e) {
  if (["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement.tagName))
    return;

  if (e.key === "ArrowRight" || e.key === "x") {
    navigateFrame(1);
  } else if (e.key === "ArrowLeft" || e.key === "z") {
    navigateFrame(-1);
  } else if (e.key.toLowerCase() === "q") {
    e.preventDefault();
    addAnnotation();
  } else if (e.key.toLowerCase() === "a") {
    e.preventDefault();
    autoAnnotate();
  } else if (e.key.toLowerCase() === "s") {
    e.preventDefault();
    saveAnnotations();
  } else if (e.key.toLowerCase() === "d") {
    e.preventDefault();
    const frameId = frames[currentFrameIndex].id;
    if (annotations[frameId] && annotations[frameId].length > 0) {
      annotations[frameId].shift(); // Remove first annotation
      updateAnnotationList();
      redrawCanvas();
    }
  } else if (e.key === "ArrowUp" || e.key === "ArrowDown") {
    e.preventDefault();
    const select = document.getElementById("labelSelect");
    const currentIndex = select.selectedIndex;
    const totalOptions = select.options.length;

    if (e.key === "ArrowUp" && currentIndex > 0) {
      select.selectedIndex = currentIndex - 1;
    } else if (e.key === "ArrowDown" && currentIndex < totalOptions - 1) {
      select.selectedIndex = currentIndex + 1;
    }
  }
});

document
  .getElementById("confidenceRange")
  .addEventListener("input", function (e) {
    const val = e.target.value;
    document.getElementById("confidenceValue").innerText = `${val}%`;
    autoAnnotate();
  });

window.onload = loadFrames;
