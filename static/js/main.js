/**
 * Entry point: app state, view switching, file selection, loading state and event wiring.
 */

import { copyQuestions } from "./action-plan.js";
import { fetchConfig, postBrief } from "./api.js";
import { $ } from "./dom.js";
import { renderBrief } from "./render.js";
import { setupTabs } from "./tabs.js";

const LOADING_STEPS = ["Reading document…", "Analysing clauses…", "Verifying sources…"];
const LOADING_STEP_MS = 1800;

const state = { file: null, limits: null, brief: null, loadingTimer: null };

/* ---------- Views & messages ---------- */

function showView(name) {
  for (const view of ["upload", "loading", "results"]) $(`${view}-view`).hidden = view !== name;
  window.scrollTo({ top: 0 });
}

function showError(message) {
  const box = $("upload-error");
  box.textContent = message;
  box.hidden = false;
}

function clearError() {
  $("upload-error").hidden = true;
}

/* ---------- Limits ---------- */

async function loadLimits() {
  try {
    state.limits = await fetchConfig();
  } catch (error) {
    showError(error.message);
    return;
  }
  for (const node of document.querySelectorAll("[data-limit]")) {
    const value = state.limits[node.dataset.limit];
    if (value !== undefined) node.textContent = Number(value).toLocaleString("en-IN");
  }
  $("mock-notice").hidden = state.limits.llm_mode !== "mock";
}

/* ---------- File selection ---------- */

function fileProblem(file) {
  const isPdf = file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
  if (!isPdf) return "Please choose a PDF file.";
  if (state.limits && file.size > state.limits.max_file_mb * 1024 * 1024) {
    return `The file is larger than ${state.limits.max_file_mb} MB.`;
  }
  return null;
}

function selectFile(file) {
  clearError();
  state.file = null;
  $("generate-btn").disabled = true;
  $("file-name").textContent = "";
  if (!file) return;

  const problem = fileProblem(file);
  if (problem) {
    showError(problem);
    return;
  }
  state.file = file;
  $("file-name").textContent = `Selected: ${file.name}`;
  $("generate-btn").disabled = false;
}

function setupDropzone() {
  const zone = $("dropzone");
  $("file-input").addEventListener("change", (event) => selectFile(event.target.files[0]));
  for (const type of ["dragenter", "dragover"]) {
    zone.addEventListener(type, (event) => {
      event.preventDefault();
      zone.classList.add("is-dragging");
    });
  }
  for (const type of ["dragleave", "drop"]) {
    zone.addEventListener(type, (event) => {
      event.preventDefault();
      zone.classList.remove("is-dragging");
    });
  }
  zone.addEventListener("drop", (event) => selectFile(event.dataTransfer.files[0]));
}

/* ---------- Loading ---------- */

function showLoadingStep(step) {
  $("loading-step").textContent = LOADING_STEPS[step];
  [...$("loading-steps").children].forEach((item, index) => {
    item.dataset.state = index < step ? "done" : index === step ? "active" : "pending";
  });
}

function startLoading() {
  let step = 0;
  showLoadingStep(step);
  showView("loading");
  $("main").setAttribute("aria-busy", "true");
  state.loadingTimer = setInterval(() => {
    step = Math.min(step + 1, LOADING_STEPS.length - 1);
    showLoadingStep(step);
  }, LOADING_STEP_MS);
}

function stopLoading() {
  clearInterval(state.loadingTimer);
  state.loadingTimer = null;
  $("main").setAttribute("aria-busy", "false");
}

/* ---------- Brief requests ---------- */

async function requestBrief(url, body) {
  clearError();
  startLoading();
  try {
    state.brief = await postBrief(url, body);
    renderBrief(state.brief);
    showView("results");
    $("results-title").focus({ preventScroll: true });
  } catch (error) {
    showView("upload");
    showError(error.message);
  } finally {
    stopLoading();
  }
}

function generateBrief(event) {
  event.preventDefault();
  if (!state.file) return;
  const body = new FormData();
  body.append("file", state.file);
  requestBrief("/api/brief", body);
}

function resetToUpload() {
  $("upload-form").reset();
  selectFile(null);
  showView("upload");
}

/* ---------- Init ---------- */

function init() {
  $("results-title").tabIndex = -1;
  setupDropzone();
  setupTabs();
  $("upload-form").addEventListener("submit", generateBrief);
  $("sample-btn").addEventListener("click", () => requestBrief("/api/brief/sample"));
  $("print-btn").addEventListener("click", () => window.print());
  $("copy-questions").addEventListener("click", () => copyQuestions(state.brief));
  $("restart-btn").addEventListener("click", resetToUpload);
  loadLimits();
}

// Module scripts run after the document is parsed, so the DOM is ready here.
init();
