// ============================================================
// CONFIG
// ============================================================
const API_BASE = "/api/v1";
const POLL_INTERVAL_MS = 1200;

// Field name the upload form sends the file under.
// Verify this matches your FastAPI endpoint's UploadFile parameter name
// in app/api/v1/images.py (commonly "file").
const UPLOAD_FIELD_NAME = "file";

const DETECTOR_SEQUENCE = [
  "Reading image metadata",
  "Measuring blur (Laplacian variance)",
  "Measuring brightness",
  "Checking for duplicates",
  "Running OCR",
  "Validating number plate",
  "Checking screenshot signals",
  "Checking photo-of-photo signals",
  "Finalizing result",
];

// ============================================================
// STATE
// ============================================================
let selectedFile = null;
let currentJobId = null;
let pollTimer = null;
let readoutTimer = null;
let readoutIndex = 0;

// Phase 7: History pagination state
let historyPage = 1;
const HISTORY_PAGE_SIZE = 5;

// ============================================================
// DOM
// ============================================================
const $ = (id) => document.getElementById(id);

const navItems = document.querySelectorAll(".nav-item");
const views = document.querySelectorAll(".view");

const dropzone = $("dropzone");
const dropzoneInner = $("dropzoneInner");
const fileInput = $("fileInput");
const scanFrame = $("scanFrame");
const previewImg = $("previewImg");
const scanLine = $("scanLine");
const scanFilename = $("scanFilename");
const scanBadge = $("scanBadge");
const uploadBtn = $("uploadBtn");
const readout = $("readout");
const readoutText = $("readoutText");

const resultsEmpty = $("resultsEmpty");
const resultsBody = $("resultsBody");
const resultsError = $("resultsError");
const resultsErrorText = $("resultsErrorText");
const resultStatusValue = $("resultStatusValue");
const resultBadge = $("resultBadge");
const metricGrid = $("metricGrid");
const issuesBlock = $("issuesBlock");
const issuesText = $("issuesText");
const ocrBlock = $("ocrBlock");
const ocrText = $("ocrText");
const timeline = $("timeline");

const apiStatusDot = $("apiStatusDot");
const apiStatusText = $("apiStatusText");

// Phase 7: pagination controls
const historyPrevBtn = $("historyPrevBtn");
const historyNextBtn = $("historyNextBtn");
const historyPageIndicator = $("historyPageIndicator");

// Phase 7: History result modal
const historyModalOverlay = $("historyModalOverlay");
const historyModalCard = $("historyModalCard");
const modalCloseBtn = $("modalCloseBtn");
const modalFileName = $("modalFileName");
const modalStatusBadge = $("modalStatusBadge");
const modalLoading = $("modalLoading");
const modalBody = $("modalBody");
const modalMetricGrid = $("modalMetricGrid");
const modalIssuesBlock = $("modalIssuesBlock");
const modalIssuesText = $("modalIssuesText");
const modalOcrBlock = $("modalOcrBlock");
const modalOcrText = $("modalOcrText");
const modalTimeline = $("modalTimeline");
const modalError = $("modalError");
const modalErrorText = $("modalErrorText");

// ============================================================
// NAVIGATION
// ============================================================
function switchView(name) {
  navItems.forEach((btn) => btn.classList.toggle("is-active", btn.dataset.view === name));
  views.forEach((v) => v.classList.toggle("is-active", v.id === `view-${name}`));
  if (name === "history") renderHistoryTable();
  if (name === "dashboard") renderDashboard();
}
navItems.forEach((btn) => btn.addEventListener("click", () => switchView(btn.dataset.view)));
document.querySelectorAll("[data-view-link]").forEach((btn) => {
  btn.addEventListener("click", () => switchView(btn.dataset.viewLink));
});

// ============================================================
// API HEALTH CHECK
// ============================================================
async function checkHealth() {
  try {
    const res = await fetch("/health");
    if (res.ok) {
      apiStatusDot.classList.add("online");
      apiStatusDot.classList.remove("offline");
      apiStatusText.textContent = "API Online";
    } else {
      throw new Error("bad status");
    }
  } catch {
    apiStatusDot.classList.add("offline");
    apiStatusDot.classList.remove("online");
    apiStatusText.textContent = "API Unreachable";
  }
}
checkHealth();
setInterval(checkHealth, 15000);

// ============================================================
// FILE SELECTION / DROPZONE
// ============================================================
dropzone.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", (e) => {
  if (e.target.files[0]) handleFileSelect(e.target.files[0]);
});

["dragenter", "dragover"].forEach((evt) =>
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.add("is-dragover");
  })
);
["dragleave", "drop"].forEach((evt) =>
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.remove("is-dragover");
  })
);
dropzone.addEventListener("drop", (e) => {
  const file = e.dataTransfer.files[0];
  if (file && file.type.startsWith("image/")) handleFileSelect(file);
});

function handleFileSelect(file) {
  selectedFile = file;
  const url = URL.createObjectURL(file);
  previewImg.src = url;
  dropzoneInner.hidden = true;
  scanFrame.hidden = false;
  scanFilename.textContent = file.name;
  setBadge(scanBadge, "ready", "READY");
  uploadBtn.disabled = false;
  resetResultsPanel();
}

// ============================================================
// UPLOAD + POLL
// ============================================================
uploadBtn.addEventListener("click", startUpload);

async function startUpload() {
  if (!selectedFile) return;

  uploadBtn.disabled = true;
  uploadBtn.textContent = "Uploading…";
  setBadge(scanBadge, "pending", "PENDING");
  scanLine.classList.add("is-active");
  startReadout();
  showResultsLoading();

  try {
    const formData = new FormData();
    formData.append(UPLOAD_FIELD_NAME, selectedFile);

    const res = await fetch(`${API_BASE}/images`, {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      const err = await safeJson(res);
      throw new Error(err?.detail || `Upload failed (${res.status})`);
    }

    const data = await res.json();
    currentJobId = data.processing_id;
    uploadBtn.textContent = "Analyzing…";
    pollJobStatus(currentJobId);
  } catch (err) {
    stopReadout();
    scanLine.classList.remove("is-active");
    setBadge(scanBadge, "failed", "ERROR");
    const friendlyMessage =
      err.message && err.message !== "Failed to fetch"
        ? err.message
        : "Couldn't reach the server. Make sure the API is running, then try again.";
    showResultsError(friendlyMessage);
    uploadBtn.disabled = false;
    uploadBtn.textContent = "Run Analysis";
  }
}

function pollJobStatus(jobId) {
  clearInterval(pollTimer);
  pollTimer = setInterval(async () => {
    try {
      const res = await fetch(`${API_BASE}/jobs/${jobId}`);
      if (!res.ok) throw new Error("Status check failed");
      const job = await res.json();

      if (job.status === "completed") {
        clearInterval(pollTimer);
        stopReadout();
        scanLine.classList.remove("is-active");
        setBadge(scanBadge, "completed", "COMPLETED");
        uploadBtn.disabled = false;
        uploadBtn.textContent = "Run Analysis";
        await fetchResult(jobId, job);
      } else if (job.status === "failed") {
        clearInterval(pollTimer);
        stopReadout();
        scanLine.classList.remove("is-active");
        setBadge(scanBadge, "failed", "FAILED");
        showResultsError(job.failure_reason || "Processing failed for an unknown reason.");
        refreshBackendData();
        uploadBtn.disabled = false;
        uploadBtn.textContent = "Run Analysis";
      }
      // pending / processing -> keep polling
    } catch (e) {
      clearInterval(pollTimer);
      stopReadout();
      showResultsError("Lost connection while checking job status.");
      uploadBtn.disabled = false;
      uploadBtn.textContent = "Run Analysis";
    }
  }, POLL_INTERVAL_MS);
}

async function fetchResult(jobId, job) {
  try {
    const res = await fetch(`${API_BASE}/jobs/${jobId}/result`);
    if (!res.ok) throw new Error("Result not available yet");
    const data = await res.json();
    renderResults(data, job);
    refreshBackendData();
  } catch (err) {
    showResultsError("Could not load analysis result.");
  } finally {
    uploadBtn.disabled = false;
    uploadBtn.textContent = "Run Analysis";
  }
}

// ============================================================
// SCANNING READOUT TICKER
// ============================================================
function startReadout() {
  readout.hidden = false;
  readoutIndex = 0;
  readoutText.textContent = DETECTOR_SEQUENCE[0];
  readoutTimer = setInterval(() => {
    readoutIndex = (readoutIndex + 1) % DETECTOR_SEQUENCE.length;
    readoutText.textContent = DETECTOR_SEQUENCE[readoutIndex];
  }, 650);
}
function stopReadout() {
  clearInterval(readoutTimer);
  readout.hidden = true;
}

// ============================================================
// RESULTS RENDERING (Upload tab)
// ============================================================
function resetResultsPanel() {
  resultsEmpty.hidden = false;
  resultsBody.hidden = true;
  resultsError.hidden = true;
}
function showResultsLoading() {
  resultsEmpty.hidden = true;
  resultsBody.hidden = true;
  resultsError.hidden = true;
}
function showResultsError(msg) {
  resultsEmpty.hidden = true;
  resultsBody.hidden = true;
  resultsError.hidden = false;
  resultsErrorText.textContent = msg;
}

function renderResults(data, job) {
  resultsEmpty.hidden = true;
  resultsError.hidden = true;
  resultsBody.hidden = false;

  resultStatusValue.textContent = data.status;
  setBadge(resultBadge, data.status, data.status.toUpperCase());

  const a = data.analysis;
  metricGrid.innerHTML = "";
  addMetric(metricGrid, "Blur Score", a.blur_score != null ? a.blur_score.toFixed(2) : "—", neutralClass());
  addMetric(metricGrid, "Brightness", a.brightness_score != null ? a.brightness_score.toFixed(2) : "—", neutralClass());
  addMetric(metricGrid, "Duplicate", a.duplicate_detected ? "Detected" : "None", flagClass(a.duplicate_detected));
  addMetric(metricGrid, "Screenshot", a.screenshot_detected ? "Detected" : "None", flagClass(a.screenshot_detected));
  addMetric(metricGrid, "Photo-of-Photo", a.photo_of_photo_detected ? "Detected" : "None", flagClass(a.photo_of_photo_detected));
  addMetric(metricGrid, "Number Plate", a.number_plate || "None found", neutralClass());
  addMetric(metricGrid, "Plate Valid", a.plate_valid ? "Yes" : "No", a.plate_valid ? passClass() : neutralClass());
  addMetric(metricGrid, "Confidence", formatConfidence(a.confidence), confidenceClass(a.confidence));

  if (a.issues) {
    issuesBlock.hidden = false;
    issuesText.textContent = a.issues;
  } else {
    issuesBlock.hidden = true;
  }

  if (a.ocr_text && a.ocr_text.trim()) {
    ocrBlock.hidden = false;
    ocrText.textContent = a.ocr_text;
  } else {
    ocrBlock.hidden = true;
  }

  timeline.innerHTML = "";
  addTimelineRow(timeline, "Created", job.created_at);
  addTimelineRow(timeline, "Started", job.started_at);
  addTimelineRow(timeline, "Completed", job.completed_at);
  addTimelineRow(timeline, "Analyzed", a.analyzed_at);
}

function addMetric(container, label, value, cls) {
  const div = document.createElement("div");
  div.className = "metric";
  div.innerHTML = `<span class="metric-label">${label}</span><span class="metric-value ${cls}">${escapeHtml(String(value))}</span>`;
  container.appendChild(div);
}
function addTimelineRow(container, label, value) {
  const row = document.createElement("div");
  row.className = "timeline-row";
  row.innerHTML = `<span class="timeline-key">${label}</span><span class="timeline-val">${value ? formatTime(value) : "—"}</span>`;
  container.appendChild(row);
}

function neutralClass() { return "neutral"; }
function passClass() { return "pass"; }
function flagClass(isFlagged) { return isFlagged ? "flag" : "pass"; }
function confidenceClass(c) {
  if (c == null) return "neutral";
  if (c >= 0.9) return "pass";
  if (c >= 0.6) return "neutral";
  return "flag";
}

// Phase 7: display confidence as a percentage instead of 0.00-1.00
function formatConfidence(c) {
  if (c == null) return "—";
  return `${Math.round(c * 100)}%`;
}

function setBadge(el, statusKey, text) {
  el.className = "badge " + (statusKey || "");
  el.textContent = text;
}

// ============================================================
// BACKEND DATA FETCHING (Phase 7: real API, no localStorage)
// ============================================================
async function fetchJobsList(page = 1, pageSize = 50) {
  const res = await fetch(`${API_BASE}/jobs?page=${page}&page_size=${pageSize}`);
  if (!res.ok) throw new Error(`Failed to load jobs (${res.status})`);
  return res.json();
}

async function fetchJobStatusOnce(jobId) {
  const res = await fetch(`${API_BASE}/jobs/${jobId}`);
  if (!res.ok) throw new Error(`Failed to load job status (${res.status})`);
  return res.json();
}

async function fetchJobResultOnce(jobId) {
  const res = await fetch(`${API_BASE}/jobs/${jobId}/result`);
  return res; // caller inspects res.ok/status since 409/422 are meaningful here
}

async function fetchAnalyticsSummary() {
  const res = await fetch(`${API_BASE}/analytics/summary`);
  if (!res.ok) throw new Error(`Failed to load analytics (${res.status})`);
  return res.json();
}

// Called after a job finishes (completed or failed) so Dashboard/History
// reflect the new job right away, regardless of which view is active.
function refreshBackendData() {
  renderDashboard();
  renderHistoryTable();
}

// ============================================================
// HISTORY (Phase 7: backed by GET /api/v1/jobs, paginated)
// ============================================================
async function renderHistoryTable() {
  const tbody = $("historyTableBody");
  const emptyEl = $("historyEmpty");
  if (!tbody || !emptyEl) return;

  try {
    const jobsData = await fetchJobsList(historyPage, HISTORY_PAGE_SIZE);
    tbody.innerHTML = "";

    const totalPages = Math.max(1, Math.ceil(jobsData.total / jobsData.page_size));

    // Guard: if we've paginated past the last page (e.g. after data shrinks),
    // snap back to the last valid page and re-fetch.
    if (jobsData.total > 0 && historyPage > totalPages) {
      historyPage = totalPages;
      return renderHistoryTable();
    }

    if (jobsData.jobs.length === 0) {
      emptyEl.hidden = false;
      updatePaginationControls(jobsData.total, jobsData.page, totalPages);
      return;
    }
    emptyEl.hidden = true;

    jobsData.jobs.forEach((j) => {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td class="file-cell">${escapeHtml(j.original_filename)}</td>
        <td><span class="badge ${j.status}">${j.status.toUpperCase()}</span></td>
        <td class="mono" style="font-size:11.5px;">${formatTime(j.created_at)}</td>
        <td class="mono">${formatConfidence(j.confidence)}</td>
        <td style="font-size:12px;">${j.issues ? escapeHtml(j.issues) : "—"}</td>
        <td class="link-cell" data-job="${j.processing_id}">View</td>
      `;
      tbody.appendChild(tr);
    });

    tbody.querySelectorAll(".link-cell").forEach((cell) => {
      cell.addEventListener("click", () => {
        openHistoryModal(cell.dataset.job);
      });
    });

    updatePaginationControls(jobsData.total, jobsData.page, totalPages);
  } catch (err) {
    tbody.innerHTML = "";
    emptyEl.hidden = false;
    emptyEl.textContent = "Couldn't load history. Make sure the API is running.";
    updatePaginationControls(0, 1, 1);
  }
}

function updatePaginationControls(total, page, totalPages) {
  if (!historyPageIndicator || !historyPrevBtn || !historyNextBtn) return;

  historyPageIndicator.textContent = `Page ${page} of ${totalPages}`;
  historyPrevBtn.disabled = page <= 1;
  historyNextBtn.disabled = page >= totalPages;
}

if (historyPrevBtn) {
  historyPrevBtn.addEventListener("click", () => {
    if (historyPage > 1) {
      historyPage -= 1;
      renderHistoryTable();
    }
  });
}

if (historyNextBtn) {
  historyNextBtn.addEventListener("click", () => {
    historyPage += 1;
    renderHistoryTable();
  });
}

$("clearHistoryBtn").addEventListener("click", () => {
  refreshBackendData();
});

// ============================================================
// HISTORY RESULT MODAL (Phase 7)
// ============================================================
function openHistoryModal(jobId) {
  if (!historyModalOverlay) return;

  historyModalOverlay.hidden = false;
  modalLoading.hidden = false;
  modalBody.hidden = true;
  modalError.hidden = true;
  modalFileName.textContent = "Loading…";
  setBadge(modalStatusBadge, "", "—");

  loadHistoryModalData(jobId);
}

function closeHistoryModal() {
  if (!historyModalOverlay) return;
  historyModalOverlay.hidden = true;
}

if (modalCloseBtn) {
  modalCloseBtn.addEventListener("click", closeHistoryModal);
}
if (historyModalOverlay) {
  historyModalOverlay.addEventListener("click", (e) => {
    if (e.target === historyModalOverlay) closeHistoryModal();
  });
}
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && historyModalOverlay && !historyModalOverlay.hidden) {
    closeHistoryModal();
  }
});

async function loadHistoryModalData(jobId) {
  try {
    const job = await fetchJobStatusOnce(jobId);

    modalFileName.textContent = jobId;
    setBadge(modalStatusBadge, job.status, job.status.toUpperCase());

    if (job.status === "failed") {
      modalLoading.hidden = true;
      modalBody.hidden = true;
      modalError.hidden = false;
      modalErrorText.textContent = job.failure_reason || "Processing failed for an unknown reason.";
      return;
    }

    if (job.status !== "completed") {
      modalLoading.hidden = true;
      modalBody.hidden = true;
      modalError.hidden = false;
      modalErrorText.textContent = `This job is still ${job.status}. Try again once it finishes.`;
      return;
    }

    const resultRes = await fetchJobResultOnce(jobId);
    if (!resultRes.ok) {
      throw new Error(`Result not available (${resultRes.status})`);
    }
    const data = await resultRes.json();

    renderModalResult(data, job);
  } catch (err) {
    modalLoading.hidden = true;
    modalBody.hidden = true;
    modalError.hidden = false;
    modalErrorText.textContent = "Could not load this result. Make sure the API is running.";
  }
}

function renderModalResult(data, job) {
  modalLoading.hidden = true;
  modalError.hidden = true;
  modalBody.hidden = false;

  modalFileName.textContent = job.processing_id;
  setBadge(modalStatusBadge, data.status, data.status.toUpperCase());

  const a = data.analysis;
  modalMetricGrid.innerHTML = "";
  addMetric(modalMetricGrid, "Blur Score", a.blur_score != null ? a.blur_score.toFixed(2) : "—", neutralClass());
  addMetric(modalMetricGrid, "Brightness", a.brightness_score != null ? a.brightness_score.toFixed(2) : "—", neutralClass());
  addMetric(modalMetricGrid, "Duplicate", a.duplicate_detected ? "Detected" : "None", flagClass(a.duplicate_detected));
  addMetric(modalMetricGrid, "Screenshot", a.screenshot_detected ? "Detected" : "None", flagClass(a.screenshot_detected));
  addMetric(modalMetricGrid, "Photo-of-Photo", a.photo_of_photo_detected ? "Detected" : "None", flagClass(a.photo_of_photo_detected));
  addMetric(modalMetricGrid, "Number Plate", a.number_plate || "None found", neutralClass());
  addMetric(modalMetricGrid, "Plate Valid", a.plate_valid ? "Yes" : "No", a.plate_valid ? passClass() : neutralClass());
  addMetric(modalMetricGrid, "Confidence", formatConfidence(a.confidence), confidenceClass(a.confidence));

  if (a.issues) {
    modalIssuesBlock.hidden = false;
    modalIssuesText.textContent = a.issues;
  } else {
    modalIssuesBlock.hidden = true;
  }

  if (a.ocr_text && a.ocr_text.trim()) {
    modalOcrBlock.hidden = false;
    modalOcrText.textContent = a.ocr_text;
  } else {
    modalOcrBlock.hidden = true;
  }

  modalTimeline.innerHTML = "";
  addTimelineRow(modalTimeline, "Created", job.created_at);
  addTimelineRow(modalTimeline, "Started", job.started_at);
  addTimelineRow(modalTimeline, "Completed", job.completed_at);
  addTimelineRow(modalTimeline, "Analyzed", a.analyzed_at);
}

// ============================================================
// DASHBOARD (Phase 7: backed by GET /api/v1/analytics/summary
// and GET /api/v1/jobs)
// ============================================================
async function renderDashboard() {
  const recentEl = $("dashboardRecent");

  try {
    const [summary, jobsData] = await Promise.all([
      fetchAnalyticsSummary(),
      fetchJobsList(1, 100),
    ]);

    $("statTotal").textContent = summary.total_jobs;
    $("statCompleted").textContent = summary.completed;
    $("statFailed").textContent = summary.failed;
    $("statIssues").textContent = jobsData.jobs.filter((j) => j.issues).length;

    if (!recentEl) return;

    if (jobsData.jobs.length === 0) {
      recentEl.innerHTML = `<div class="empty-state">
          <p class="empty-title">No jobs yet</p>
          <p class="empty-sub">Upload an image to start the inspection pipeline.</p>
        </div>`;
      return;
    }

    recentEl.innerHTML = "";
    jobsData.jobs.slice(0, 6).forEach((j) => {
      const row = document.createElement("div");
      row.className = "recent-row";
      row.innerHTML = `
        <span class="recent-name">${escapeHtml(j.original_filename)}</span>
        <span class="badge ${j.status}">${j.status.toUpperCase()}</span>
        <span class="recent-time">${formatConfidence(j.confidence)}</span>
        <span class="recent-time">${formatTime(j.created_at)}</span>
      `;
      recentEl.appendChild(row);
    });
  } catch (err) {
    if (recentEl) {
      recentEl.innerHTML = `<div class="empty-state">
          <p class="empty-title">Couldn't load dashboard data</p>
          <p class="empty-sub">Make sure the API is running, then refresh.</p>
        </div>`;
    }
  }
}

// ============================================================
// UTIL
// ============================================================
function formatTime(iso) {
  try {
    const d = new Date(iso);
    return d.toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
  } catch {
    return iso;
  }
}
function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}
async function safeJson(res) {
  try { return await res.json(); } catch { return null; }
}

// ============================================================
// INIT
// ============================================================
renderDashboard();