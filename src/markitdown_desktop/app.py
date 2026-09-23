# MarkItDown Desktop - convert PDF files to Markdown on macOS.
# Copyright (C) 2026 MarkItDown Desktop contributors
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Desktop front-end for Microsoft MarkItDown."""

from __future__ import annotations

import base64
import os
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

import webview
from markitdown import MarkItDown

APP_NAME = "MarkItDown Desktop"
APP_VERSION = "1.0.0"


def resource_path(*parts: str) -> str:
    """Resolve a bundled resource both from source and from a PyInstaller build."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)


def md_filename(pdf_name: str) -> str:
    stem = Path(pdf_name).stem or "document"
    return f"{stem}.md"


class Api:
    """Methods exposed to the web UI as `window.pywebview.api.*`."""

    def __init__(self) -> None:
        self._md = MarkItDown(enable_plugins=False)
        self._lock = threading.Lock()
        self._window: webview.Window | None = None

    # ---- conversion -------------------------------------------------------

    def _convert_path(self, path: str) -> dict:
        try:
            with self._lock:  # MarkItDown instance is not guaranteed thread-safe
                result = self._md.convert(path)
            text = (result.text_content or "").strip() + "\n"
            if not text.strip():
                return {
                    "ok": False,
                    "error": "No text found. The PDF may be scanned images only (no OCR).",
                }
            return {"ok": True, "markdown": text}
        except Exception as exc:  # surface any converter error to the UI
            return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}

    def pick_files(self) -> list[dict]:
        """Open the native file picker and return the selected PDFs."""
        paths = self._window.create_file_dialog(
            webview.OPEN_DIALOG,
            allow_multiple=True,
            file_types=("PDF documents (*.pdf)",),
        )
        return [{"path": p, "name": os.path.basename(p)} for p in (paths or [])]

    def convert_path(self, path: str) -> dict:
        return self._convert_path(path)

    def convert_data(self, name: str, data_b64: str) -> dict:
        """Convert a file dropped onto the window (sent as base64 from the UI)."""
        suffix = Path(name).suffix or ".pdf"
        fd, tmp = tempfile.mkstemp(suffix=suffix)
        try:
            with os.fdopen(fd, "wb") as fh:
                fh.write(base64.b64decode(data_b64))
            return self._convert_path(tmp)
        finally:
            try:
                os.remove(tmp)
            except OSError:
                pass

    # ---- saving -----------------------------------------------------------

    def save_one(self, pdf_name: str, markdown: str) -> dict:
        target = self._window.create_file_dialog(
            webview.SAVE_DIALOG,
            save_filename=md_filename(pdf_name),
            file_types=("Markdown (*.md)",),
        )
        if not target:
            return {"ok": False, "cancelled": True}
        if isinstance(target, (list, tuple)):
            target = target[0]
        if not target.lower().endswith(".md"):
            target += ".md"
        Path(target).write_text(markdown, encoding="utf-8")
        return {"ok": True, "path": target}

    def save_all(self, items: list[dict]) -> dict:
        folder = self._window.create_file_dialog(webview.FOLDER_DIALOG)
        if not folder:
            return {"ok": False, "cancelled": True}
        if isinstance(folder, (list, tuple)):
            folder = folder[0]
        written, used = [], set()
        for item in items:
            name = md_filename(item["name"])
            stem, n = Path(name).stem, 1
            # avoid overwriting when two PDFs share a name, or a file already exists
            while name in used or (Path(folder) / name).exists():
                n += 1
                name = f"{stem} ({n}).md"
            used.add(name)
            (Path(folder) / name).write_text(item["markdown"], encoding="utf-8")
            written.append(name)
        return {"ok": True, "folder": folder, "files": written}

    def copy_text(self, text: str) -> dict:
        """Copy to the macOS clipboard (the web clipboard API is unreliable in WKWebView)."""
        try:
            subprocess.run(
                ["pbcopy"],
                input=text.encode("utf-8"),
                check=True,
                env={**os.environ, "LANG": "en_US.UTF-8"},
            )
            return {"ok": True}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def reveal(self, path: str) -> None:
        subprocess.run(["open", "-R", path], check=False)

    def app_info(self) -> dict:
        return {"name": APP_NAME, "version": APP_VERSION}


def main() -> None:
    # Headless mode, handy for scripting and for testing a packaged build:
    #   "MarkItDown Desktop.app/Contents/MacOS/MarkItDown Desktop" --convert file.pdf
    if len(sys.argv) > 2 and sys.argv[1] == "--convert":
        api = Api()
        status = 0
        for path in sys.argv[2:]:
            res = api.convert_path(path)
            if res["ok"]:
                sys.stdout.write(res["markdown"])
            else:
                sys.stderr.write(f"{path}: {res['error']}\n")
                status = 1
        sys.exit(status)

    api = Api()
    window = webview.create_window(
        APP_NAME,
        url=resource_path("ui", "index.html"),
        js_api=api,
        width=1200,
        height=780,
        min_size=(860, 560),
    )
    api._window = window
    webview.start(debug=bool(os.environ.get("MID_DEBUG")))


if __name__ == "__main__":
    main()
