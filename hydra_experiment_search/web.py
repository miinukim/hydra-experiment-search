from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import argparse
import json
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

DEFAULT_CONFIG_GLOB = "**/results/resolved_config.yaml"
DEFAULT_CONFIG_NAME = "resolved_config.yaml"


HTML = """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>experiment search</title>
  <style>
    :root {
      --bg: #fff8ef;
      --bg-2: #ffe0f1;
      --panel: rgba(255, 255, 255, 0.94);
      --panel-soft: #fffdf8;
      --border: rgba(236, 72, 153, 0.18);
      --text: #26183a;
      --muted: #6f5a7d;
      --accent: #db2777;
      --accent-2: #7c3aed;
      --accent-3: #f59e0b;
      --shadow: 0 18px 44px rgba(124, 58, 237, 0.12);
    }
    * { box-sizing: border-box; }
    body {
      font-family: "Trebuchet MS", "Avenir Next", "Segoe UI", sans-serif;
      margin: 0;
      background:
        radial-gradient(circle at top left, rgba(245, 158, 11, 0.28), transparent 26%),
        radial-gradient(circle at top right, rgba(236, 72, 153, 0.22), transparent 25%),
        radial-gradient(circle at bottom right, rgba(124, 58, 237, 0.18), transparent 28%),
        linear-gradient(180deg, var(--bg) 0%, var(--bg-2) 100%);
      color: var(--text);
    }
    .shell { max-width: 1460px; margin: 0 auto; padding: 22px 20px 36px; }
    .topbar {
      margin-bottom: 14px;
      padding: 18px 20px;
      border-radius: 20px;
      background: linear-gradient(135deg, rgba(124, 58, 237, 0.92) 0%, rgba(236, 72, 153, 0.88) 55%, rgba(245, 158, 11, 0.78) 100%);
      color: white;
      box-shadow: 0 22px 48px rgba(219, 39, 119, 0.16);
    }
    .topbar h1 { margin: 0; font-size: 2rem; letter-spacing: 0.02em; }
    .topbar p { margin: 8px 0 0; max-width: 900px; line-height: 1.45; color: rgba(255, 255, 255, 0.9); }
    .controls {
      background: linear-gradient(135deg, rgba(255, 255, 255, 0.95) 0%, rgba(255, 247, 252, 0.92) 100%);
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 18px;
      box-shadow: var(--shadow);
      margin-bottom: 14px;
    }
    .row { display: flex; gap: 12px; margin-bottom: 12px; align-items: center; }
    .row-top { align-items: stretch; }
    label {
      min-width: 110px;
      font-size: 0.9rem;
      font-weight: 600;
      color: #5b2167;
      letter-spacing: 0.01em;
    }
    input, textarea, button { font: inherit; }
    input, textarea {
      border: 1px solid var(--border);
      border-radius: 12px;
      width: 100%;
      background: rgba(255, 255, 255, 0.88);
      padding: 11px 13px;
      color: var(--text);
      transition: border-color 0.15s ease, box-shadow 0.15s ease;
    }
    input:focus, textarea:focus {
      outline: none;
      border-color: rgba(236, 72, 153, 0.5);
      box-shadow: 0 0 0 4px rgba(236, 72, 153, 0.12);
    }
    button {
      border: 0;
      border-radius: 12px;
      background: linear-gradient(135deg, var(--accent) 0%, var(--accent-2) 58%, var(--accent-3) 100%);
      color: white;
      cursor: pointer;
      padding: 11px 16px;
      font-weight: 600;
      box-shadow: 0 12px 24px rgba(219, 39, 119, 0.22);
    }
    button:hover { filter: saturate(1.08) brightness(1.02); }
    .filters-field { flex: 1; }
    .search-button { align-self: stretch; white-space: nowrap; }
    .split { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 16px; align-items: stretch; }
    .split > div { min-width: 0; }
    .panel {
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 18px;
      padding: 16px 18px;
      margin-top: 16px;
      box-shadow: var(--shadow);
      backdrop-filter: blur(8px);
      min-width: 0;
    }
    .panel h3 { margin: 0 0 10px 0; }
    .tab-panel { height: 68vh; min-height: 460px; display: flex; flex-direction: column; }
    .tab-body { flex: 1; min-height: 0; min-width: 0; }
    .summary-line {
      margin: 0 0 10px;
      padding: 10px 12px;
      border-radius: 12px;
      background: linear-gradient(90deg, rgba(236, 72, 153, 0.08) 0%, rgba(124, 58, 237, 0.08) 100%);
    }
    table { border-collapse: collapse; width: 100%; }
    th, td { text-align: left; border-bottom: 1px solid rgba(124, 58, 237, 0.10); padding: 9px 8px; vertical-align: top; }
    th {
      position: sticky;
      top: 0;
      background: linear-gradient(180deg, #fff7fb 0%, #fff2f7 100%);
      font-size: 0.82rem;
      text-transform: uppercase;
      letter-spacing: 0.04em;
      color: var(--muted);
    }
    tr:hover { background: #fff2fb; cursor: pointer; }
    .muted { color: var(--muted); font-size: 0.95rem; }
    pre { white-space: pre-wrap; word-break: break-word; margin: 0; }
    .preview-box {
      height: 100%;
      overflow: auto;
      border: 1px solid rgba(124, 58, 237, 0.14);
      border-radius: 14px;
      padding: 12px;
      background: var(--panel-soft);
    }
    .table-wrap { max-height: 220px; max-width: 100%; overflow: auto; border: 1px solid rgba(124, 58, 237, 0.14); border-radius: 12px; margin: 8px 0 16px 0; background: rgba(255, 255, 255, 0.95); }
    .artifact-list { margin: 8px 0 16px 18px; }
    .plot-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; margin-top: 8px; }
    .plot-card { border: 1px solid rgba(236, 72, 153, 0.16); border-radius: 14px; padding: 10px; background: rgba(255, 255, 255, 0.96); box-shadow: 0 10px 24px rgba(245, 158, 11, 0.10); }
    .plot-card img { width: 100%; height: auto; display: block; border-radius: 6px; }
    .plot-link { display: block; }
    .autocomplete { position: relative; }
    .suggestions { position: absolute; top: calc(100% + 4px); left: 122px; right: 0; background: rgba(255, 255, 255, 0.98); border: 1px solid rgba(236, 72, 153, 0.18); border-radius: 14px; box-shadow: 0 12px 32px rgba(124, 58, 237, 0.14); max-height: 220px; overflow: auto; z-index: 20; }
    .suggestion { padding: 8px 10px; border-bottom: 1px solid rgba(124, 58, 237, 0.08); }
    .suggestion:last-child { border-bottom: 0; }
    .suggestion.active { background: linear-gradient(90deg, rgba(236, 72, 153, 0.12) 0%, rgba(124, 58, 237, 0.12) 100%); color: #0f172a; }
    .table-shell { max-height: 420px; max-width: 100%; overflow: auto; border: 1px solid rgba(124, 58, 237, 0.14); border-radius: 14px; background: rgba(255, 255, 255, 0.97); }
    a { color: #7c3aed; }
    a:hover { color: #db2777; }
    .lightbox {
      position: fixed; inset: 0; display: none; align-items: center; justify-content: center;
      padding: 28px; background: rgba(39, 16, 57, 0.72); backdrop-filter: blur(6px); z-index: 100;
    }
    .lightbox.open { display: flex; }
    .lightbox-card {
      max-width: min(1200px, 92vw); max-height: 90vh; width: fit-content; display: flex; flex-direction: column;
      gap: 10px; padding: 14px; border-radius: 18px; background: rgba(255, 252, 253, 0.98);
      border: 1px solid rgba(255, 255, 255, 0.55); box-shadow: 0 28px 64px rgba(20, 9, 33, 0.34);
    }
    .lightbox-head { display: flex; justify-content: space-between; align-items: center; gap: 12px; color: var(--muted); font-size: 0.92rem; }
    .lightbox-close {
      border: 0; border-radius: 999px; width: 34px; height: 34px; padding: 0; font-size: 1.1rem; line-height: 1;
      box-shadow: none; background: linear-gradient(135deg, rgba(236, 72, 153, 0.14) 0%, rgba(124, 58, 237, 0.14) 100%); color: var(--text);
    }
    .lightbox-close:hover { background: linear-gradient(135deg, rgba(236, 72, 153, 0.22) 0%, rgba(124, 58, 237, 0.22) 100%); }
    .lightbox-image { max-width: min(1160px, 88vw); max-height: calc(90vh - 72px); width: auto; height: auto; border-radius: 10px; display: block; }
    @media (max-width: 1100px) {
      .split { grid-template-columns: 1fr; }
      .suggestions { left: 0; }
      label { min-width: 90px; }
    }
  </style>
</head>
<body>
  <div class="shell">
  <div class="topbar">
    <h1>Experiment Search</h1>
    <p>Search Hydra outputs by resolved config fields, inspect plots, and preview result tables directly in the browser.</p>
  </div>
  <div class="controls">
    <div class="row" style="margin-top:16px;">
      <label>Outputs root</label>
      <input id="root" value="" />
    </div>
    <div class="row row-top autocomplete" style="margin-bottom:0;">
      <label>Filters</label>
      <textarea id="filters" class="filters-field" rows="2" placeholder="Comma-separated filters like model.depth=6, trainer.max_epochs>=50"></textarea>
      <button class="search-button" onclick="search()">Search</button>
      <div id="suggestions" class="suggestions" style="display:none;"></div>
    </div>
    <div class="muted" style="margin-left:122px; margin-top:10px;">Supported operators: =, !=, &gt;=, &lt;=, &gt;, &lt;, ~ (substring). Press Enter to search, Tab to autocomplete.</div>
  </div>
  <div class="panel">
    <div id="summary" class="muted summary-line">No search yet.</div>
    <div class="table-shell">
      <table id="results">
        <thead>
          <tr>
            <th>Date</th>
            <th>Time</th>
            <th>Run Dir</th>
            <th>Config</th>
            <th>CSV Files</th>
          </tr>
        </thead>
        <tbody></tbody>
      </table>
    </div>
  </div>
  <div class="split">
    <div>
      <div class="panel tab-panel">
        <h3>Experiment Details</h3>
        <div class="tab-body preview-box">
          <pre id="details">Select a row to inspect the flattened record.</pre>
        </div>
      </div>
    </div>
    <div>
      <div class="panel tab-panel">
        <h3>Data Preview</h3>
        <div id="data-preview" class="tab-body preview-box muted">Select a row to load result tables and artifacts.</div>
      </div>
    </div>
  </div>
  <div id="lightbox" class="lightbox" aria-hidden="true">
    <div class="lightbox-card">
      <div class="lightbox-head">
        <div id="lightbox-title"></div>
        <button class="lightbox-close" type="button" onclick="closeLightbox()">×</button>
      </div>
      <img id="lightbox-image" class="lightbox-image" alt="" />
    </div>
  </div>
  </div>
<script>
let lastResults = [];
let fieldSummary = { keys: [], numeric_keys: [], sample_values: {} };
let activeSuggestion = 0;
let currentSuggestions = [];
function openLightbox(src, title) {
  const box = document.getElementById("lightbox");
  document.getElementById("lightbox-image").src = src;
  document.getElementById("lightbox-image").alt = title || "artifact preview";
  document.getElementById("lightbox-title").textContent = title || "";
  box.classList.add("open");
  box.setAttribute("aria-hidden", "false");
}
function closeLightbox() {
  const box = document.getElementById("lightbox");
  box.classList.remove("open");
  box.setAttribute("aria-hidden", "true");
  document.getElementById("lightbox-image").src = "";
}
function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}
async function loadFieldSummary(root) {
  const response = await fetch("/api/fields?root=" + encodeURIComponent(root));
  const payload = await response.json();
  fieldSummary = payload;
}
function tokenInfo(text) {
  const parts = text.split(",");
  const token = parts[parts.length - 1].trim();
  return { token, prefix: parts.slice(0, -1).join(",").trim() };
}
function suggestionPool(token) {
  const ops = ["!=", ">=", "<=", "=", ">", "<", "~"];
  for (const op of ops) {
    const idx = token.indexOf(op);
    if (idx >= 0) {
      const key = token.slice(0, idx).trim();
      const valuePrefix = token.slice(idx + op.length).trim();
      const values = (fieldSummary.sample_values && fieldSummary.sample_values[key]) || [];
      return values
        .filter((value) => value.toLowerCase().startsWith(valuePrefix.toLowerCase()))
        .map((value) => `${key}${op}${value}`);
    }
  }
  return (fieldSummary.keys || [])
    .filter((key) => key.toLowerCase().includes(token.toLowerCase()))
    .map((key) => `${key}=`);
}
function renderSuggestions() {
  const box = document.getElementById("suggestions");
  if (!currentSuggestions.length) {
    box.style.display = "none";
    box.innerHTML = "";
    return;
  }
  box.style.display = "block";
  box.innerHTML = currentSuggestions
    .map((item, index) => `<div class="suggestion ${index === activeSuggestion ? "active" : ""}" data-index="${index}">${escapeHtml(item)}</div>`)
    .join("");
  for (const el of box.querySelectorAll(".suggestion")) {
    el.onclick = () => applySuggestion(Number(el.dataset.index));
  }
}
function updateSuggestions() {
  const filters = document.getElementById("filters").value;
  const { token } = tokenInfo(filters);
  currentSuggestions = token ? suggestionPool(token).slice(0, 12) : [];
  activeSuggestion = 0;
  renderSuggestions();
}
function applySuggestion(index = 0) {
  if (!currentSuggestions.length) {
    return;
  }
  const filtersBox = document.getElementById("filters");
  const { prefix } = tokenInfo(filtersBox.value);
  const chosen = currentSuggestions[index];
  filtersBox.value = prefix ? `${prefix}, ${chosen}` : chosen;
  currentSuggestions = [];
  renderSuggestions();
}
async function search() {
  const root = document.getElementById("root").value;
  const filters = document.getElementById("filters").value;
  const params = new URLSearchParams({ root, filters });
  const response = await fetch("/api/search?" + params.toString());
  const payload = await response.json();
  const tbody = document.querySelector("#results tbody");
  tbody.innerHTML = "";
  lastResults = payload.results || [];
  document.getElementById("summary").textContent = payload.summary;
  for (const [index, record] of lastResults.entries()) {
    const tr = document.createElement("tr");
    tr.onclick = () => showDetails(index);
    tr.innerHTML = `
      <td>${record["_date"] ?? ""}</td>
      <td>${record["_time"] ?? ""}</td>
      <td>${record["_run_dir"] ?? ""}</td>
      <td>${record["_config_name"] ?? ""}</td>
      <td>${Array.isArray(record["_csv_files"]) ? record["_csv_files"].join(", ") : ""}</td>
    `;
    tbody.appendChild(tr);
  }
}
function showDetails(index) {
  const record = lastResults[index];
  const ordered = Object.keys(record).sort().map((key) => `${key}: ${JSON.stringify(record[key])}`);
  document.getElementById("details").textContent = ordered.join("\\n");
  loadData(record["_results_dir"]);
}
async function loadData(resultsDir) {
  const root = document.getElementById("root").value;
  const params = new URLSearchParams({ results_dir: resultsDir });
  const response = await fetch("/api/details?" + params.toString());
  const payload = await response.json();
  const box = document.getElementById("data-preview");
  if (!response.ok) {
    box.textContent = payload.summary || "Failed to load details.";
    return;
  }
  let html = `<div class="muted">Results dir: ${escapeHtml(payload.results_dir)}</div>`;
  if (payload.artifacts.length) {
    const imageArtifacts = payload.artifacts.filter((artifact) => artifact.is_image);
    const otherArtifacts = payload.artifacts.filter((artifact) => !artifact.is_image);
    if (imageArtifacts.length) {
      html += `<h4>Plots</h4><div class="plot-grid">`;
      for (const artifact of imageArtifacts) {
        const href = "/artifact?path=" + encodeURIComponent(artifact.path) + "&root=" + encodeURIComponent(root);
        html += `<div class="plot-card"><div class="muted">${escapeHtml(artifact.name)}</div><a class="plot-link" href="${href}" data-preview-src="${href}" data-preview-title="${escapeHtml(artifact.name)}"><img src="${href}" alt="${escapeHtml(artifact.name)}" /></a></div>`;
      }
      html += `</div>`;
    }
    if (otherArtifacts.length) {
      html += `<h4>Artifacts</h4><ul class="artifact-list">`;
      for (const artifact of otherArtifacts) {
        const href = "/artifact?path=" + encodeURIComponent(artifact.path) + "&root=" + encodeURIComponent(root);
        html += `<li><a href="${href}" target="_blank">${escapeHtml(artifact.name)}</a></li>`;
      }
      html += `</ul>`;
    }
  }
  for (const table of payload.csv_tables) {
    html += `<h4>${escapeHtml(table.name)}</h4>`;
    if (!table.columns.length) {
      html += `<div class="muted">No rows available.</div>`;
      continue;
    }
    html += `<div class="muted">Showing up to ${table.row_limit} rows.</div>`;
    html += `<div class="table-wrap"><table><thead><tr>${table.columns.map((c) => `<th>${escapeHtml(c)}</th>`).join("")}</tr></thead><tbody>`;
    for (const row of table.rows) {
      html += `<tr>${table.columns.map((c) => `<td>${escapeHtml(row[c] ?? "")}</td>`).join("")}</tr>`;
    }
    html += `</tbody></table></div>`;
  }
  if (payload.config_text) {
    html += `<h4>${escapeHtml(payload.config_name)}</h4><pre>${escapeHtml(payload.config_text)}</pre>`;
  }
  box.innerHTML = html;
  for (const link of box.querySelectorAll(".plot-link")) {
    link.addEventListener("click", (event) => {
      event.preventDefault();
      openLightbox(link.dataset.previewSrc, link.dataset.previewTitle || "");
    });
  }
}
document.getElementById("root").value = "__DEFAULT_ROOT__";
document.getElementById("lightbox").addEventListener("click", (event) => {
  if (event.target.id === "lightbox") {
    closeLightbox();
  }
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") {
    closeLightbox();
  }
});
document.getElementById("filters").addEventListener("input", updateSuggestions);
document.getElementById("filters").addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey && !currentSuggestions.length) {
    event.preventDefault();
    search();
    return;
  }
  if (event.key === "Tab" && currentSuggestions.length) {
    event.preventDefault();
    applySuggestion(activeSuggestion);
    return;
  }
  if (event.key === "ArrowDown" && currentSuggestions.length) {
    event.preventDefault();
    activeSuggestion = Math.min(activeSuggestion + 1, currentSuggestions.length - 1);
    renderSuggestions();
  }
  if (event.key === "ArrowUp" && currentSuggestions.length) {
    event.preventDefault();
    activeSuggestion = Math.max(activeSuggestion - 1, 0);
    renderSuggestions();
  }
  if (event.key === "Enter" && currentSuggestions.length) {
    event.preventDefault();
    applySuggestion(activeSuggestion);
  }
});
loadFieldSummary(document.getElementById("root").value).then(search);
</script>
</body>
</html>
"""


class Handler(BaseHTTPRequestHandler):
    default_root = "outputs"
    config_glob = DEFAULT_CONFIG_GLOB
    config_name = DEFAULT_CONFIG_NAME

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/":
            self._send_html()
            return
        if parsed.path == "/api/search":
            self._send_search(parsed.query)
            return
        if parsed.path == "/api/fields":
            self._send_fields(parsed.query)
            return
        if parsed.path == "/api/details":
            self._send_details(parsed.query)
            return
        if parsed.path == "/artifact":
            self._send_artifact(parsed.query)
            return
        self.send_error(HTTPStatus.NOT_FOUND, "Not found")

    def _send_html(self) -> None:
        body = HTML.replace("__DEFAULT_ROOT__", self.default_root).encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_search(self, query: str) -> None:
        from .index import filter_experiments, index_experiments

        params = parse_qs(query)
        root = params.get("root", [self.default_root])[0]
        raw_filters = params.get("filters", [""])[0]
        filters = [part.strip() for part in raw_filters.split(",") if part.strip()]
        try:
            records = index_experiments(root, config_glob=self.config_glob, config_name=self.config_name)
            matches = filter_experiments(records, filters)
            payload = {
                "summary": f"Found {len(matches)} matching experiments under {Path(root).expanduser()}",
                "results": [record.data for record in matches],
            }
            body = json.dumps(payload).encode("utf-8")
            self.send_response(HTTPStatus.OK)
        except Exception as exc:
            body = json.dumps({"summary": f"Search failed: {exc}", "results": []}).encode("utf-8")
            self.send_response(HTTPStatus.BAD_REQUEST)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_fields(self, query: str) -> None:
        from .index import index_experiments, summarize_fields

        params = parse_qs(query)
        root = params.get("root", [self.default_root])[0]
        try:
            records = index_experiments(root, config_glob=self.config_glob, config_name=self.config_name)
            body = json.dumps(summarize_fields(records)).encode("utf-8")
            self.send_response(HTTPStatus.OK)
        except Exception as exc:
            body = json.dumps({"keys": [], "numeric_keys": [], "sample_values": {}, "summary": str(exc)}).encode("utf-8")
            self.send_response(HTTPStatus.BAD_REQUEST)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_details(self, query: str) -> None:
        from .index import load_experiment_details

        params = parse_qs(query)
        results_dir = params.get("results_dir", [""])[0]
        try:
            body = json.dumps(load_experiment_details(results_dir, config_name=self.config_name)).encode("utf-8")
            self.send_response(HTTPStatus.OK)
        except Exception as exc:
            body = json.dumps({"summary": f"Detail load failed: {exc}"}).encode("utf-8")
            self.send_response(HTTPStatus.BAD_REQUEST)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_artifact(self, query: str) -> None:
        params = parse_qs(query)
        raw_path = params.get("path", [""])[0]
        raw_root = params.get("root", [self.default_root])[0]
        path = Path(unquote(raw_path)).expanduser().resolve()
        default_root = Path(unquote(raw_root)).expanduser().resolve()
        if default_root not in path.parents and path != default_root:
          self.send_error(HTTPStatus.FORBIDDEN, "Artifact path outside outputs root")
          return
        if not path.exists() or not path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "Artifact not found")
            return
        mime = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".svg": "image/svg+xml",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".txt": "text/plain; charset=utf-8",
            ".yaml": "text/plain; charset=utf-8",
            ".yml": "text/plain; charset=utf-8",
            ".log": "text/plain; charset=utf-8",
        }.get(path.suffix.lower(), "application/octet-stream")
        body = path.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def build_parser(default_root: str = "outputs") -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Web UI for searching Hydra experiment outputs.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--root", default=default_root, help="Default outputs root shown in the UI.")
    parser.add_argument("--config-glob", default=DEFAULT_CONFIG_GLOB, help="Glob used to locate resolved config files.")
    parser.add_argument("--config-name", default=DEFAULT_CONFIG_NAME, help="Config filename rendered in the preview pane.")
    return parser


def parse_web_args(argv: list[str] | None = None, default_root: str = "outputs") -> argparse.Namespace:
    parser = build_parser(default_root=default_root)
    return parser.parse_args(argv)


def build_web_handler(
    root: str = "outputs",
    config_glob: str = DEFAULT_CONFIG_GLOB,
    config_name: str = DEFAULT_CONFIG_NAME,
) -> type[BaseHTTPRequestHandler]:
    class ConfiguredHandler(Handler):
        pass

    ConfiguredHandler.default_root = str(Path(root).expanduser())
    ConfiguredHandler.config_glob = config_glob
    ConfiguredHandler.config_name = config_name

    return ConfiguredHandler


def serve(
    host: str = "127.0.0.1",
    port: int = 8765,
    root: str = "outputs",
    config_glob: str = DEFAULT_CONFIG_GLOB,
    config_name: str = DEFAULT_CONFIG_NAME,
) -> None:
    handler = build_web_handler(root=root, config_glob=config_glob, config_name=config_name)
    server = ThreadingHTTPServer((host, port), handler)
    print(f"Serving experiment search at http://{host}:{port}")
    server.serve_forever()


def main(argv: list[str] | None = None, default_root: str = "outputs") -> None:
    args = parse_web_args(argv=argv, default_root=default_root)
    serve(
        host=args.host,
        port=args.port,
        root=args.root,
        config_glob=args.config_glob,
        config_name=args.config_name,
    )


if __name__ == "__main__":
    main()
