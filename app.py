#!/usr/bin/env python3
"""
Solari Board — Flask backend
Routes:
  GET  /                  → display page
  GET  /send              → message submission form
  POST /send              → save message, redirect back
  GET  /send?msg=...      → save message via URL param
  GET  /api/message       → JSON {message: str} polled by display
  GET  /calibrate         → calibration page
  POST /api/calibrate     → save device calibration
  GET  /api/calibrate     → get all saved calibrations
"""

from flask import Flask, request, jsonify, render_template_string, redirect
import json, pathlib

app = Flask(__name__)

DATA_FILE   = pathlib.Path(__file__).parent / "message.json"
CAL_FILE    = pathlib.Path(__file__).parent / "calibrations.json"
DEFAULT_MSG = "WELCOME"

# ── Persistence ────────────────────────────────────────────────────────────────

def read_message() -> str:
    try:
        return json.loads(DATA_FILE.read_text()).get("message", DEFAULT_MSG)
    except Exception:
        return DEFAULT_MSG

def write_message(msg: str) -> None:
    DATA_FILE.write_text(json.dumps({"message": msg}, ensure_ascii=False))

def read_calibrations() -> dict:
    try:
        return json.loads(CAL_FILE.read_text())
    except Exception:
        return {}

def write_calibration(device: str, cols: int, rows: int, cell_size: int) -> None:
    cals = read_calibrations()
    cals[device] = {"cols": cols, "rows": rows, "cellSize": cell_size}
    CAL_FILE.write_text(json.dumps(cals, indent=2))

# ── Sanitize ───────────────────────────────────────────────────────────────────

DISPLAY_CHARS = set(" ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,!?-:/()@#")

SUBSTITUTIONS = {
    "\u2026": "...",  # ellipsis
    "\u2018": "'",    # left single quote
    "\u2019": "'",    # right single quote
    "\u201c": '"',    # left double quote
    "\u201d": '"',    # right double quote
    "\u2013": "-",    # en dash
    "\u2014": "-",    # em dash
    "\u00e9": "E",    "\u00e8": "E",    "\u00e0": "A",
    "\u00fc": "U",    "\u00f6": "O",    "\u00e4": "A",    "\u00f1": "N",
}

def sanitize(msg: str) -> str:
    for src, dst in SUBSTITUTIONS.items():
        msg = msg.replace(src, dst)
    msg = msg.upper()
    msg = "".join(ch for ch in msg if ch in DISPLAY_CHARS)
    msg = " ".join(msg.split())
    return msg or DEFAULT_MSG

def sanitize_device_name(name: str) -> str:
    """Lowercase, alphanumeric + hyphens only, max 32 chars."""
    name = name.lower().strip()
    name = "".join(c if c.isalnum() or c in "-_ " else "" for c in name)
    name = name.replace(" ", "-").replace("_", "-")
    name = "-".join(p for p in name.split("-") if p)  # collapse dashes
    return name[:32] or "unnamed"

# ── API ────────────────────────────────────────────────────────────────────────

@app.route("/api/message")
def api_message():
    return jsonify({"message": read_message()})

@app.route("/api/calibrate", methods=["GET"])
def api_calibrate_get():
    return jsonify(read_calibrations())

@app.route("/api/calibrate", methods=["POST"])
def api_calibrate_post():
    data = request.get_json(force=True)
    device    = sanitize_device_name(data.get("device", "unnamed"))
    cols      = int(data.get("cols", 10))
    rows      = int(data.get("rows", 3))
    cell_size = int(data.get("cellSize", 52))
    write_calibration(device, cols, rows, cell_size)
    return jsonify({"ok": True, "device": device, "cols": cols, "rows": rows, "cellSize": cell_size})

# ── Send form ──────────────────────────────────────────────────────────────────

SEND_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Post a Message · Solari Board</title>
  <style>
    :root {
      --bg: #080808; --panel: #111; --border: #222;
      --amber: #e8a020; --amber-dim: #7a4a00;
      --text: #d4d4d4; --muted: #555; --radius: 12px;
      --mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Courier New", monospace;
    }
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      min-height: 100vh; background: var(--bg); color: var(--text);
      font-family: var(--mono); display: grid; place-items: center; padding: 24px;
    }
    .card {
      background: var(--panel); border: 1px solid var(--border);
      border-radius: var(--radius); padding: 40px 36px;
      width: 100%; max-width: 560px;
      box-shadow: 0 20px 60px rgba(0,0,0,0.7);
    }
    .eyebrow { font-size: 11px; letter-spacing: 0.18em; text-transform: uppercase; color: var(--amber); margin-bottom: 10px; }
    h1 { font-size: 26px; font-weight: 700; color: #f0f0f0; margin-bottom: 32px; }
    label { display: block; font-size: 11px; letter-spacing: 0.12em; text-transform: uppercase; color: var(--muted); margin-bottom: 8px; }
    textarea {
      width: 100%; background: #0d0d0d; border: 1px solid var(--border);
      border-radius: 8px; color: var(--text); font-family: var(--mono);
      font-size: 18px; letter-spacing: 0.05em; padding: 14px 16px;
      outline: none; resize: vertical; min-height: 120px;
      transition: border-color 0.15s; -webkit-user-select: text; user-select: text;
    }
    textarea:focus { border-color: var(--amber-dim); box-shadow: 0 0 0 3px rgba(232,160,32,0.08); }
    textarea::placeholder { color: #333; }
    .char-count { font-size: 11px; color: var(--muted); margin-top: 6px; text-align: right; }
    .hint { font-size: 11px; color: var(--muted); margin-top: 4px; }
    .preview-label { font-size: 11px; letter-spacing: 0.12em; text-transform: uppercase; color: var(--muted); margin: 20px 0 8px; }
    .preview {
      background: #0d0d0d; border: 1px solid var(--border); border-radius: 8px;
      padding: 12px 16px; font-size: 16px; letter-spacing: 0.05em;
      color: var(--amber); min-height: 46px; word-break: break-word; max-height: 200px; overflow-y: auto;
    }
    button {
      margin-top: 24px; width: 100%; background: var(--amber); color: #000;
      border: none; border-radius: 8px; font-family: var(--mono);
      font-size: 13px; font-weight: 700; letter-spacing: 0.14em;
      text-transform: uppercase; padding: 15px; cursor: pointer;
      transition: background 0.15s, transform 0.1s;
    }
    button:hover { background: #f0b030; }
    button:active { transform: scale(0.98); }
    .links { display: flex; justify-content: space-between; margin-top: 24px; }
    .nav-link { font-size: 12px; color: var(--muted); text-decoration: none; letter-spacing: 0.08em; transition: color 0.15s; }
    .nav-link:hover { color: var(--amber); }
    .flash { background: rgba(232,160,32,0.1); border: 1px solid var(--amber-dim); border-radius: 8px; padding: 12px 16px; font-size: 13px; color: var(--amber); margin-bottom: 24px; letter-spacing: 0.04em; }
  </style>
</head>
<body>
  <div class="card">
    <p class="eyebrow">Solari Board</p>
    <h1>Post a message</h1>
    {% if flash %}<div class="flash">✓ Board updated — flipping now.</div>{% endif %}
    <form method="POST" action="/send">
      <label for="msg">Message</label>
      <textarea id="msg" name="msg" placeholder="Type or paste your message here…"
        autocomplete="off" autocorrect="off" autocapitalize="off"
        spellcheck="false" maxlength="9999">{{ current }}</textarea>
      <div class="char-count"><span id="char-count">0</span> characters</div>
      <p class="hint">No limit · converted to uppercase · special characters cleaned up automatically</p>
      <p class="preview-label">Preview (as it will appear)</p>
      <div class="preview" id="preview">{{ current }}</div>
      <button type="submit">Post to board</button>
    </form>
    <div class="links">
      <a class="nav-link" href="/">← View the board</a>
      <a class="nav-link" href="/calibrate">Calibrate a display →</a>
    </div>
  </div>
  <script>
    const SUBS = {"\u2026":"...","\u2018":"'","\u2019":"'","\u201c":'"',"\u201d":'"',"\u2013":"-","\u2014":"-"};
    const ALLOWED = new Set(" ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.,!?-:/()@#");
    function sanitize(str) {
      for (const [s,d] of Object.entries(SUBS)) str = str.replaceAll(s,d);
      str = str.toUpperCase();
      str = [...str].filter(c => ALLOWED.has(c)).join("");
      return str.replace(/  +/g," ").trim();
    }
    const textarea = document.getElementById("msg");
    const preview  = document.getElementById("preview");
    const counter  = document.getElementById("char-count");
    function update() {
      const clean = sanitize(textarea.value);
      preview.textContent = clean || "—";
      counter.textContent = clean.length;
    }
    textarea.addEventListener("input", update);
    textarea.addEventListener("paste", () => setTimeout(update, 50));
    update();
  </script>
</body>
</html>
"""

@app.route("/send", methods=["GET"])
def send_get():
    url_msg = request.args.get("msg", "").strip()
    if url_msg:
        write_message(sanitize(url_msg))
        return redirect("/send?sent=1")
    flash = request.args.get("sent") == "1"
    return render_template_string(SEND_HTML, current=read_message(), flash=flash)

@app.route("/send", methods=["POST"])
def send_post():
    raw = request.form.get("msg", "")
    write_message(sanitize(raw))
    return redirect("/send?sent=1")

# ── Calibration page ───────────────────────────────────────────────────────────

CALIBRATE_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Calibrate · Solari Board</title>
  <style>
    :root {
      --bg: #000; --panel: #0e0e0e; --border: #1f1f1f;
      --amber: #e8a020; --amber-dim: #7a4a00;
      --text: #d4d4d4; --muted: #444; --radius: 10px;
      --mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Courier New", monospace;
    }
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body { background: var(--bg); color: var(--text); font-family: var(--mono); overflow: hidden; }

    /* ── Step 1: name entry ── */
    #step-name {
      min-height: 100vh; display: grid; place-items: center; padding: 24px;
    }
    .name-card {
      background: var(--panel); border: 1px solid var(--border);
      border-radius: 14px; padding: 40px 36px; width: 100%; max-width: 480px;
      box-shadow: 0 20px 60px rgba(0,0,0,0.8);
    }
    .eyebrow { font-size: 11px; letter-spacing: 0.18em; text-transform: uppercase; color: var(--amber); margin-bottom: 10px; }
    h1 { font-size: 24px; font-weight: 700; color: #f0f0f0; margin-bottom: 8px; }
    .subtitle { font-size: 13px; color: var(--muted); margin-bottom: 32px; line-height: 1.5; }
    label { display: block; font-size: 11px; letter-spacing: 0.12em; text-transform: uppercase; color: var(--muted); margin-bottom: 8px; }
    input[type=text] {
      width: 100%; background: #0d0d0d; border: 1px solid var(--border);
      border-radius: 8px; color: var(--text); font-family: var(--mono);
      font-size: 20px; padding: 14px 16px; outline: none;
      transition: border-color 0.15s;
    }
    input[type=text]:focus { border-color: var(--amber-dim); box-shadow: 0 0 0 3px rgba(232,160,32,0.08); }
    input[type=text]::placeholder { color: #2a2a2a; }
    .hint { font-size: 11px; color: var(--muted); margin-top: 8px; }
    .btn {
      margin-top: 28px; width: 100%; background: var(--amber); color: #000;
      border: none; border-radius: 8px; font-family: var(--mono);
      font-size: 13px; font-weight: 700; letter-spacing: 0.14em;
      text-transform: uppercase; padding: 15px; cursor: pointer;
      transition: background 0.15s, transform 0.1s;
    }
    .btn:hover { background: #f0b030; }
    .btn:active { transform: scale(0.98); }

    /* ── Step 2: calibration grid ── */
    #step-grid { display: none; position: fixed; inset: 0; flex-direction: column; }

    .grid-header {
      background: #000;
      padding: 12px 20px;
      display: flex; align-items: center; justify-content: space-between;
      border-bottom: 1px solid #1a1a1a;
      flex-shrink: 0;
    }
    .grid-header h2 { font-size: 13px; letter-spacing: 0.1em; color: var(--muted); text-transform: uppercase; }
    .grid-instructions { font-size: 12px; color: #333; letter-spacing: 0.05em; }

    .grid-area {
      flex: 1;
      overflow: hidden;
      padding: 12px;
      display: flex;
      flex-direction: column;
      gap: 0;
    }

    .grid-row { display: flex; }

    .grid-cell {
      border: 1px solid #1e1e1e;
      border-radius: 6px;
      display: grid; place-items: center;
      cursor: pointer;
      font-size: 11px;
      color: #2a2a2a;
      background: #0a0a0a;
      transition: background 0.1s, color 0.1s, border-color 0.1s;
      flex-shrink: 0;
      user-select: none;
    }
    .grid-cell:hover { background: #1a1a1a; color: #555; border-color: #333; }
    .grid-cell.col-selected { background: #1a1200; border-color: var(--amber-dim); color: var(--amber); }
    .grid-cell.row-selected { background: #001a00; border-color: #1a5c1a; color: #3a9a3a; }
    .grid-cell.both-selected { background: #1a0a00; border-color: var(--amber); color: var(--amber); }

    .grid-footer {
      background: #000;
      padding: 12px 20px;
      border-top: 1px solid #1a1a1a;
      display: flex; align-items: center; justify-content: space-between;
      flex-shrink: 0; gap: 16px;
    }
    .selection-status { font-size: 12px; color: var(--muted); letter-spacing: 0.05em; flex: 1; }
    .selection-status span { color: var(--amber); }
    .btn-sm {
      background: var(--amber); color: #000; border: none; border-radius: 8px;
      font-family: var(--mono); font-size: 12px; font-weight: 700;
      letter-spacing: 0.1em; text-transform: uppercase; padding: 10px 20px;
      cursor: pointer; white-space: nowrap; opacity: 0.3; pointer-events: none;
      transition: opacity 0.2s, background 0.15s;
    }
    .btn-sm.ready { opacity: 1; pointer-events: auto; }
    .btn-sm.ready:hover { background: #f0b030; }

    /* ── Step 3: confirmation ── */
    #step-confirm { display: none; min-height: 100vh; place-items: center; padding: 24px; }
    .confirm-card {
      background: var(--panel); border: 1px solid var(--border);
      border-radius: 14px; padding: 40px 36px; width: 100%; max-width: 480px;
      box-shadow: 0 20px 60px rgba(0,0,0,0.8);
    }
    .confirm-card h1 { font-size: 24px; color: #f0f0f0; margin-bottom: 24px; }
    .settings-table { width: 100%; border-collapse: collapse; margin-bottom: 28px; }
    .settings-table td { padding: 10px 0; border-bottom: 1px solid #1a1a1a; font-size: 14px; }
    .settings-table td:first-child { color: var(--muted); font-size: 11px; letter-spacing: 0.1em; text-transform: uppercase; }
    .settings-table td:last-child { color: var(--amber); text-align: right; }
    .nav-link { font-size: 12px; color: var(--muted); text-decoration: none; letter-spacing: 0.08em; }
    .nav-link:hover { color: var(--amber); }
  </style>
</head>
<body>

  <!-- Step 1: Name your device -->
  <div id="step-name">
    <div class="name-card">
      <p class="eyebrow">Solari Board</p>
      <h1>Calibrate this display</h1>
      <p class="subtitle">First, give this display a name. Then you'll tap the last fully visible cell to set its constraints.</p>
      <label for="device-name">Display name</label>
      <input id="device-name" type="text" placeholder="e.g. lobby, bar-screen, kitchen" maxlength="32"
        autocomplete="off" autocorrect="off" autocapitalize="off" spellcheck="false"/>
      <p class="hint">Lowercase letters, numbers, and hyphens only.</p>
      <button class="btn" id="btn-start">Next — set up the grid →</button>
    </div>
  </div>

  <!-- Step 2: Tap the grid -->
  <div id="step-grid">
    <div class="grid-header">
      <h2 id="grid-device-label">Calibrating: —</h2>
      <p class="grid-instructions">Tap the last fully visible cell in the top row, then the last fully visible cell in the left column</p>
    </div>
    <div class="grid-area" id="grid-area"></div>
    <div class="grid-footer">
      <p class="selection-status" id="sel-status">
        Step 1 of 2 — tap the last fully visible <span>column</span>
      </p>
      <button class="btn-sm" id="btn-save">Save calibration</button>
    </div>
  </div>

  <!-- Step 3: Confirmation -->
  <div id="step-confirm">
    <div class="confirm-card">
      <p class="eyebrow">Solari Board</p>
      <h1>✓ Calibration saved</h1>
      <table class="settings-table">
        <tr><td>Display name</td><td id="conf-name">—</td></tr>
        <tr><td>Columns</td><td id="conf-cols">—</td></tr>
        <tr><td>Rows</td><td id="conf-rows">—</td></tr>
        <tr><td>Cell size</td><td id="conf-size">—</td></tr>
      </table>
      <div style="display:flex;justify-content:space-between;align-items:center">
        <a class="nav-link" href="/">← View the board</a>
        <a class="nav-link" href="/calibrate">Calibrate another →</a>
      </div>
    </div>
  </div>

  <script>
    // ── Constants ────────────────────────────────────────────────────
    const CELL_SIZES = [52, 44, 36, 28];
    const GAP        = 6;
    const H_PAD      = 24;  // grid-area padding each side
    const V_PAD      = 95;  // header + footer combined height

    // ── State ────────────────────────────────────────────────────────
    let deviceName = "";
    let cellSize   = 52;
    let totalCols  = 0;
    let totalRows  = 0;
    let selCol     = null;  // 1-indexed, selected by user
    let selRow     = null;  // 1-indexed, selected by user

    // ── Step 1: name entry ───────────────────────────────────────────
    const stepName = document.getElementById("step-name");
    const stepGrid = document.getElementById("step-grid");
    const stepConf = document.getElementById("step-confirm");
    const nameInput = document.getElementById("device-name");

    function sanitizeDeviceName(n) {
      return n.toLowerCase().replace(/[^a-z0-9\- ]/g,"").trim()
               .replace(/[\s_]+/g,"-").replace(/-+/g,"-").slice(0,32) || "unnamed";
    }

    document.getElementById("btn-start").addEventListener("click", () => {
      deviceName = sanitizeDeviceName(nameInput.value);
      if (!deviceName || deviceName === "unnamed") {
        nameInput.focus(); return;
      }
      document.getElementById("grid-device-label").textContent = "Calibrating: " + deviceName;
      buildGrid();
      stepName.style.display = "none";
      stepGrid.style.display = "flex";
    });

    nameInput.addEventListener("keydown", e => {
      if (e.key === "Enter") document.getElementById("btn-start").click();
    });

    // ── Step 2: build the grid ───────────────────────────────────────
    function buildGrid() {
      const availW = window.innerWidth  - H_PAD * 2;
      const availH = window.innerHeight - V_PAD;

      // Pick largest cell size giving at least 5 cols and 3 rows
      cellSize = CELL_SIZES[CELL_SIZES.length - 1];
      for (const s of CELL_SIZES) {
        const c = Math.floor((availW + GAP) / (s + GAP));
        const r = Math.floor((availH + GAP) / (s + GAP));
        if (c >= 5 && r >= 3) { cellSize = s; break; }
      }

      totalCols = Math.floor((availW + GAP) / (cellSize + GAP));
      totalRows = Math.floor((availH + GAP) / (cellSize + GAP));
      selCol = null; selRow = null;
      updateSaveButton();

      const area = document.getElementById("grid-area");
      area.innerHTML = "";
      area.style.gap = GAP + "px";

      for (let r = 1; r <= totalRows; r++) {
        const rowEl = document.createElement("div");
        rowEl.className = "grid-row";
        rowEl.style.gap = GAP + "px";
        rowEl.style.marginBottom = r < totalRows ? GAP + "px" : "0";

        for (let c = 1; c <= totalCols; c++) {
          const cell = document.createElement("div");
          cell.className  = "grid-cell";
          cell.style.width  = cellSize + "px";
          cell.style.height = cellSize + "px";
          cell.dataset.col  = c;
          cell.dataset.row  = r;

          // Label: top row shows column numbers, left col shows row numbers, corner shows both
          if (r === 1 && c === 1)      cell.textContent = "1,1";
          else if (r === 1)            cell.textContent = c;
          else if (c === 1)            cell.textContent = r;
          // else leave blank

          cell.addEventListener("click", onCellClick);
          rowEl.appendChild(cell);
        }
        area.appendChild(rowEl);
      }
    }

    function onCellClick(e) {
      const c = parseInt(e.currentTarget.dataset.col);
      const r = parseInt(e.currentTarget.dataset.row);

      if (selCol === null) {
        // First tap — selecting column
        selCol = c;
        highlightCols();
        updateStatus();
      } else if (selRow === null) {
        // Second tap — selecting row
        selRow = r;
        highlightRows();
        updateStatus();
        updateSaveButton();
      } else {
        // Third tap resets
        selCol = null; selRow = null;
        clearHighlights();
        updateStatus();
        updateSaveButton();
      }
    }

    function highlightCols() {
      document.querySelectorAll(".grid-cell").forEach(cell => {
        const c = parseInt(cell.dataset.col);
        const r = parseInt(cell.dataset.row);
        cell.classList.toggle("col-selected", c === selCol && selRow === null);
        cell.classList.toggle("both-selected", c === selCol && selRow !== null && r === selRow);
      });
    }

    function highlightRows() {
      document.querySelectorAll(".grid-cell").forEach(cell => {
        const c = parseInt(cell.dataset.col);
        const r = parseInt(cell.dataset.row);
        const isSelCol = c === selCol;
        const isSelRow = r === selRow;
        cell.classList.remove("col-selected","row-selected","both-selected");
        if (isSelCol && isSelRow) cell.classList.add("both-selected");
        else if (isSelCol)        cell.classList.add("col-selected");
        else if (isSelRow)        cell.classList.add("row-selected");
      });
    }

    function clearHighlights() {
      document.querySelectorAll(".grid-cell").forEach(cell =>
        cell.classList.remove("col-selected","row-selected","both-selected")
      );
    }

    function updateStatus() {
      const el = document.getElementById("sel-status");
      if (selCol === null) {
        el.innerHTML = `Step 1 of 2 — tap the last fully visible <span>column</span>`;
      } else if (selRow === null) {
        el.innerHTML = `Step 2 of 2 — column <span>${selCol}</span> saved · now tap the last fully visible <span>row</span>`;
      } else {
        el.innerHTML = `Column <span>${selCol}</span> · Row <span>${selRow}</span> · tap Save to confirm`;
      }
    }

    function updateSaveButton() {
      const btn = document.getElementById("btn-save");
      btn.classList.toggle("ready", selCol !== null && selRow !== null);
    }

    // ── Save calibration ─────────────────────────────────────────────
    document.getElementById("btn-save").addEventListener("click", async () => {
      if (selCol === null || selRow === null) return;
      try {
        const res = await fetch("/api/calibrate", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ device: deviceName, cols: selCol, rows: selRow, cellSize }),
        });
        const data = await res.json();
        showConfirmation(data);
      } catch (err) {
        alert("Save failed — check the Flask service is running.");
      }
    });

    function showConfirmation(data) {
      document.getElementById("conf-name").textContent = data.device;
      document.getElementById("conf-cols").textContent = data.cols;
      document.getElementById("conf-rows").textContent = data.rows;
      document.getElementById("conf-size").textContent = data.cellSize + "px";
      stepGrid.style.display  = "none";
      stepConf.style.display  = "grid";
    }

    // Rebuild grid on resize
    let resizeTimer;
    window.addEventListener("resize", () => {
      if (stepGrid.style.display !== "none") {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(buildGrid, 300);
      }
    });
  </script>
</body>
</html>
"""

@app.route("/calibrate")
def calibrate():
    return render_template_string(CALIBRATE_HTML)

# ── Display page ───────────────────────────────────────────────────────────────

@app.route("/")
def display():
    with open(pathlib.Path(__file__).parent / "display.html") as f:
        return f.read()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
