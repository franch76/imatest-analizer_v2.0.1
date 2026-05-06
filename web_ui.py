"""Simple local web UI for Imatest SFRreg batch analysis."""

from __future__ import annotations

import sys
import logging
import threading
from pathlib import Path
from typing import List

from flask import Flask, jsonify, render_template_string, request

ROOT_DIR = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)).resolve()
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.runner import run_analysis_split


app = Flask(__name__)

LOG_BUFFER: List[str] = []
LOG_LOCK = threading.Lock()
WORKER: threading.Thread | None = None
CANCEL_FLAG = threading.Event()


class BufferHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        msg = self.format(record)
        with LOG_LOCK:
            LOG_BUFFER.append(msg)


def setup_logging() -> None:
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    handler = BufferHandler()
    handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    root.handlers = [handler]


def is_running() -> bool:
    return WORKER is not None and WORKER.is_alive()


@app.route("/", methods=["GET"])
def index():
    html = """
    <!doctype html>
    <html lang="en">
    <head>
      <meta charset="utf-8" />
      <title>Imatest SFRreg Batch Analysis</title>
      <style>
        body { font-family: Arial, sans-serif; margin: 24px; }
        fieldset { border: 1px solid #999; padding: 12px; margin-bottom: 12px; }
        legend { font-weight: bold; }
        label { display:block; margin-top: 8px; }
        input[type=text] { width: 80%; padding: 6px; }
        button { margin-right: 8px; padding: 6px 12px; }
        #log { border: 1px solid #666; height: 260px; overflow: auto; padding: 8px; background: #111; color: #eee; font-family: monospace; }
      </style>
    </head>
    <body>
      <h2>Imatest SFRreg Batch Analysis</h2>

      <fieldset>
        <legend>Input</legend>
        <label>Before folder or JSON files</label>
        <input id="before_path" type="text" placeholder="/path/to/init_or_before" />
        <label>After folder or JSON files</label>
        <input id="after_path" type="text" placeholder="/path/to/after_test_or_after" />
      </fieldset>

      <fieldset>
        <legend>Output</legend>
        <label>Output folder</label>
        <input id="output_path" type="text" placeholder="/path/to/output_ES2" />
      </fieldset>

      <fieldset>
        <legend>Execution</legend>
        <label><input id="exclude_missing" type="checkbox" /> Exclude missing pairs (use only matched Before/After keys)</label>
        <button onclick="start()">Analyze</button>
        <button onclick="stop()">Stop</button>
        <button onclick="location.reload()">Refresh</button>
      </fieldset>

      <fieldset>
        <legend>Progress Log</legend>
        <div id="log"></div>
      </fieldset>

      <fieldset>
        <legend>Help</legend>
        <div>About: Imatest SFRreg JSON batch analysis tool.</div>
        <div>Usage: Fill Before/After input paths and output path, then click Analyze.</div>
      </fieldset>

      <script>
        let logPos = 0;
        function appendLog(lines) {
          const log = document.getElementById('log');
          lines.forEach(line => {
            const div = document.createElement('div');
            div.textContent = line;
            log.appendChild(div);
          });
          log.scrollTop = log.scrollHeight;
        }

        async function poll() {
          const res = await fetch(`/logs?pos=${logPos}`);
          const data = await res.json();
          logPos = data.next_pos;
          appendLog(data.lines);
          setTimeout(poll, 1000);
        }

        async function start() {
          const beforeInput = document.getElementById('before_path').value;
          const afterInput = document.getElementById('after_path').value;
          const output = document.getElementById('output_path').value;
          const excludeMissing = document.getElementById('exclude_missing').checked;
          await fetch('/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              before_path: beforeInput,
              after_path: afterInput,
              output_path: output,
              exclude_missing_pairs: excludeMissing
            })
          });
        }

        async function stop() {
          await fetch('/stop', { method: 'POST' });
        }

        poll();
      </script>
    </body>
    </html>
    """
    return render_template_string(html)


@app.route("/start", methods=["POST"])
def start():
    global WORKER
    if is_running():
        return ("Already running", 409)

    payload = request.get_json(force=True)
    before_path = payload.get("before_path", "").strip()
    after_path = payload.get("after_path", "").strip()
    output_path = payload.get("output_path", "").strip()
    exclude_missing = bool(payload.get("exclude_missing_pairs"))
    if not before_path or not after_path or not output_path:
        return ("Before/after/output path required", 400)

    CANCEL_FLAG.clear()

    def worker():
        try:
            run_analysis_split(
                Path(before_path),
                Path(after_path),
                Path(output_path),
                CANCEL_FLAG.is_set,
                exclude_missing,
            )
        except Exception as exc:
            logging.getLogger(__name__).exception("Analysis failed: %s", exc)

    WORKER = threading.Thread(target=worker, daemon=True)
    WORKER.start()
    return ("OK", 200)


@app.route("/stop", methods=["POST"])
def stop():
    CANCEL_FLAG.set()
    return ("OK", 200)


@app.route("/logs", methods=["GET"])
def logs():
    pos = int(request.args.get("pos", 0))
    with LOG_LOCK:
        lines = LOG_BUFFER[pos:]
        next_pos = len(LOG_BUFFER)
    return jsonify({"lines": lines, "next_pos": next_pos})


if __name__ == "__main__":
    setup_logging()
    app.run(host="127.0.0.1", port=5000, debug=False)
