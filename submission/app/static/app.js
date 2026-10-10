const MAX_BYTES = 10 * 1024 * 1024;
const ALLOWED = ["pdf", "docx", "txt"];
const $ = (id) => document.getElementById(id);
const drop = $("drop"), input = $("file"), result = $("result");
const progress = $("progress"), errorEl = $("error"), upload = $("upload");

let downloadUrl = null;

function showError(msg) {
  errorEl.hidden = !msg;
  errorEl.textContent = msg || "";
}

function showUploader() {
  progress.hidden = true;
  drop.hidden = false;
  upload.hidden = false;
}

function highlight(preEl, text) {
  preEl.textContent = "";
  text.split(/(\*)/).forEach((part) => {
    if (part === "*") {
      const m = document.createElement("mark");
      m.textContent = "*";
      preEl.appendChild(m);
    } else {
      preEl.appendChild(document.createTextNode(part));
    }
  });
}

function base64ToBlob(b64, mime) {
  const bytes = Uint8Array.from(atob(b64), (c) => c.charCodeAt(0));
  return new Blob([bytes], { type: mime });
}

function formatSize(n) {
  return n < 1024 * 1024 ? `${(n / 1024).toFixed(1)} KB` : `${(n / 1024 / 1024).toFixed(1)} MB`;
}

async function handleFile(file) {
  showError("");
  const ext = file.name.split(".").pop().toLowerCase();
  if (!ALLOWED.includes(ext)) return showError("Unsupported file. Please choose a PDF, DOCX or TXT file.");
  if (file.size === 0 || file.size > MAX_BYTES) return showError("File must be between 1 byte and 10 MB.");

  result.hidden = true;
  drop.hidden = true;
  progress.hidden = false;
  $("pname").textContent = file.name;
  try {
    const res = await fetch("/api/anonymize", {
      method: "POST",
      headers: { "X-Filename": encodeURIComponent(file.name) },
      body: file,
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || "Something went wrong.");

    if (downloadUrl) URL.revokeObjectURL(downloadUrl);
    downloadUrl = URL.createObjectURL(base64ToBlob(data.data, data.mime));
    const link = $("download");
    link.href = downloadUrl;
    link.download = data.filename;

    const icon = $("ficon");
    icon.textContent = ext.toUpperCase();
    icon.className = `ficon ${ext}`;
    $("fname").textContent = data.filename;
    $("fsize").textContent = formatSize(file.size);
    $("count").textContent = `${data.count} item${data.count === 1 ? "" : "s"} censored // ${data.engine === "gemini" ? "Gemini AI" : "built-in rules, Gemini unavailable"}`;
    $("original").textContent = data.original;
    highlight($("censored"), data.censored);

    upload.hidden = true;
    result.hidden = false;
    result.scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (err) {
    showUploader();
    showError(err.message);
  }
}

$("browse").addEventListener("click", (e) => { e.stopPropagation(); input.click(); });
drop.addEventListener("click", () => input.click());
drop.addEventListener("keydown", (e) => {
  if (e.key === "Enter" || e.key === " ") { e.preventDefault(); input.click(); }
});
input.addEventListener("change", () => {
  if (input.files[0]) handleFile(input.files[0]);
  input.value = "";
});

["dragenter", "dragover"].forEach((ev) =>
  drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add("over"); }));
drop.addEventListener("dragleave", () => drop.classList.remove("over"));
drop.addEventListener("drop", (e) => {
  e.preventDefault();
  drop.classList.remove("over");
  if (e.dataTransfer.files[0]) handleFile(e.dataTransfer.files[0]);
});
// Stop the browser from opening a file dropped outside the zone.
["dragover", "drop"].forEach((ev) => window.addEventListener(ev, (e) => e.preventDefault()));

$("reset").addEventListener("click", () => {
  result.hidden = true;
  showError("");
  showUploader();
  window.scrollTo({ top: 0, behavior: "smooth" });
});
