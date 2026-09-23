// MarkItDown Desktop - GPL-3.0-or-later
(function () {
  "use strict";

  const $ = (id) => document.getElementById(id);
  const files = [];          // { id, name, size, status: 'pending'|'converting'|'done'|'error', markdown, error, source }
  let activeId = null;
  let view = "raw";
  let nextId = 1;
  let queue = Promise.resolve();

  const ICON = {
    ok: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 5-6"/></svg>',
    err: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M12 8v5m0 3h.01"/></svg>',
    wait: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9" stroke-dasharray="3 3"/></svg>',
    x: '<svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6 6 18"/></svg>',
  };

  // ---- backend bridge ----------------------------------------------------
  let api = null;
  const apiReady = new Promise((resolve) => {
    if (window.pywebview && window.pywebview.api) resolve(window.pywebview.api);
    window.addEventListener("pywebviewready", () => resolve(window.pywebview.api));
  }).then((a) => (api = a));

  // ---- helpers -----------------------------------------------------------
  const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const fmtSize = (n) => (n == null ? "" : n < 1024 * 1024 ? `${Math.max(1, Math.round(n / 1024))} KB` : `${(n / 1048576).toFixed(1)} MB`);
  const isPdf = (name) => /\.pdf$/i.test(name);

  let toastTimer;
  function toast(msg) {
    const t = $("toast");
    t.textContent = msg;
    t.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => t.classList.remove("show"), 2400);
  }

  function readAsBase64(file) {
    return new Promise((resolve, reject) => {
      const r = new FileReader();
      r.onload = () => resolve(String(r.result).split(",")[1] || "");
      r.onerror = () => reject(r.error);
      r.readAsDataURL(file);
    });
  }

  // ---- adding + converting ----------------------------------------------
  function addEntries(entries) {
    let skipped = 0;
    for (const e of entries) {
      if (!isPdf(e.name)) { skipped++; continue; }
      const item = { id: nextId++, name: e.name, size: e.size, status: "pending", source: e };
      files.push(item);
      if (activeId == null) activeId = item.id;
      queue = queue.then(() => convert(item));
    }
    if (skipped) toast(`Skipped ${skipped} non-PDF file${skipped > 1 ? "s" : ""}`);
    render();
  }

  async function convert(item) {
    if (!files.includes(item)) return; // removed while waiting
    item.status = "converting";
    render();
    await apiReady;
    let res;
    try {
      const src = item.source;
      if (src.path) res = await api.convert_path(src.path);
      else res = await api.convert_data(item.name, await readAsBase64(src.file));
    } catch (err) {
      res = { ok: false, error: String(err && err.message ? err.message : err) };
    }
    delete item.source;
    if (res && res.ok) { item.status = "done"; item.markdown = res.markdown; }
    else { item.status = "error"; item.error = (res && res.error) || "Unknown error"; }
    render();
  }

  // ---- rendering ---------------------------------------------------------
  function render() {
    const list = $("file-list");
    list.innerHTML = files.map((f) => {
      const state =
        f.status === "done" ? `<span class="state ok" title="Converted">${ICON.ok}</span>` :
        f.status === "error" ? `<span class="state err" title="Failed">${ICON.err}</span>` :
        f.status === "converting" ? `<span class="state"><div class="spinner"></div></span>` :
        `<span class="state" title="Queued">${ICON.wait}</span>`;
      const sub =
        f.status === "done" ? `${f.markdown.length.toLocaleString()} characters` :
        f.status === "error" ? "Conversion failed" :
        f.status === "converting" ? "Converting…" : `Queued · ${fmtSize(f.size)}`;
      return `<li class="file${f.id === activeId ? " active" : ""}" data-id="${f.id}">
        ${state}
        <div style="min-width:0"><div class="name" title="${esc(f.name)}">${esc(f.name)}</div><div class="sub">${sub}</div></div>
        <button class="x" data-remove="${f.id}" title="Remove">${ICON.x}</button>
      </li>`;
    }).join("");

    $("count").textContent = files.length;
    $("btn-clear").hidden = files.length === 0;
    const doneCount = files.filter((f) => f.status === "done").length;
    $("btn-save-all").disabled = doneCount === 0;
    $("btn-save-all").lastChild.textContent = doneCount > 1 ? `Download all .md (${doneCount})` : "Download all .md";

    const f = files.find((x) => x.id === activeId);
    $("empty").hidden = !!f;
    $("viewer").hidden = !f;
    if (!f) return;

    $("v-name").textContent = f.name;
    const status = $("v-status");
    const done = f.status === "done";
    $("btn-copy").disabled = !done;
    $("btn-save").disabled = !done;

    if (done) {
      const words = (f.markdown.match(/\S+/g) || []).length;
      const lines = f.markdown.split("\n").length;
      $("v-meta").textContent = `${words.toLocaleString()} words · ${lines.toLocaleString()} lines · ${f.markdown.length.toLocaleString()} characters`;
      status.hidden = true;
      if ($("v-raw").dataset.id !== String(f.id)) {
        $("v-raw").textContent = f.markdown;
        $("v-raw").dataset.id = f.id;
        $("v-raw").scrollTop = 0;
        $("v-rendered").dataset.id = "";
      }
      if (view === "rendered" && $("v-rendered").dataset.id !== String(f.id)) {
        $("v-rendered").innerHTML = window.renderMarkdown(f.markdown);
        $("v-rendered").dataset.id = f.id;
        $("v-rendered").scrollTop = 0;
      }
      $("v-raw").hidden = view !== "raw";
      $("v-rendered").hidden = view !== "rendered";
    } else {
      $("v-meta").textContent = fmtSize(f.size);
      $("v-raw").hidden = true;
      $("v-rendered").hidden = true;
      $("v-raw").dataset.id = "";
      status.hidden = false;
      status.className = "status" + (f.status === "error" ? " err" : "");
      status.innerHTML = f.status === "error"
        ? `${ICON.err}<span>${esc(f.error)}</span>`
        : `<div class="spinner"></div><span>${f.status === "converting" ? "Converting with MarkItDown…" : "Waiting in queue…"}</span>`;
    }
  }

  // ---- actions -----------------------------------------------------------
  async function pickFiles() {
    await apiReady;
    const picked = await api.pick_files();
    if (picked && picked.length) addEntries(picked.map((p) => ({ name: p.name, path: p.path, size: null })));
  }

  async function copyActive() {
    const f = files.find((x) => x.id === activeId);
    if (!f || f.status !== "done") return;
    await apiReady;
    const res = await api.copy_text(f.markdown);
    if (res && res.ok) {
      const b = $("btn-copy");
      b.classList.add("done");
      b.querySelector("span").textContent = "Copied!";
      setTimeout(() => { b.classList.remove("done"); b.querySelector("span").textContent = "Copy"; }, 1600);
    } else toast("Could not copy to clipboard");
  }

  async function saveActive() {
    const f = files.find((x) => x.id === activeId);
    if (!f || f.status !== "done") return;
    await apiReady;
    const res = await api.save_one(f.name, f.markdown);
    if (res && res.ok) toast(`Saved ${res.path.split("/").pop()}`);
  }

  async function saveAll() {
    const done = files.filter((f) => f.status === "done");
    if (!done.length) return;
    await apiReady;
    const res = await api.save_all(done.map((f) => ({ name: f.name, markdown: f.markdown })));
    if (res && res.ok) {
      toast(`Saved ${res.files.length} file${res.files.length > 1 ? "s" : ""} to ${res.folder.split("/").pop()}`);
      api.reveal(res.folder + "/" + res.files[0]);
    }
  }

  function setView(v) {
    view = v;
    $("tab-raw").classList.toggle("active", v === "raw");
    $("tab-rendered").classList.toggle("active", v === "rendered");
    render();
  }

  // ---- events ------------------------------------------------------------
  $("btn-add").addEventListener("click", pickFiles);
  $("dropzone").addEventListener("click", pickFiles);
  $("dropzone").addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); pickFiles(); } });
  $("btn-copy").addEventListener("click", copyActive);
  $("btn-save").addEventListener("click", saveActive);
  $("btn-save-all").addEventListener("click", saveAll);
  $("tab-raw").addEventListener("click", () => setView("raw"));
  $("tab-rendered").addEventListener("click", () => setView("rendered"));
  $("btn-clear").addEventListener("click", () => { files.length = 0; activeId = null; render(); });

  $("file-list").addEventListener("click", (e) => {
    const rm = e.target.closest("[data-remove]");
    if (rm) {
      const id = +rm.dataset.remove;
      const idx = files.findIndex((f) => f.id === id);
      if (idx >= 0) files.splice(idx, 1);
      if (activeId === id) activeId = files.length ? files[Math.min(idx, files.length - 1)].id : null;
      render();
      return;
    }
    const li = e.target.closest(".file");
    if (li) { activeId = +li.dataset.id; render(); }
  });

  document.addEventListener("keydown", (e) => {
    if (!e.metaKey) return;
    if (e.key === "o") { e.preventDefault(); pickFiles(); }
    else if (e.key === "s") { e.preventDefault(); e.shiftKey ? saveAll() : saveActive(); }
    else if (e.key === "c" && e.shiftKey) { e.preventDefault(); copyActive(); }
  });

  // drag & drop anywhere in the window
  let dragDepth = 0;
  const hasFiles = (e) => e.dataTransfer && Array.from(e.dataTransfer.types || []).includes("Files");
  window.addEventListener("dragenter", (e) => { if (!hasFiles(e)) return; e.preventDefault(); dragDepth++; document.body.classList.add("dragging"); });
  window.addEventListener("dragover", (e) => { if (!hasFiles(e)) return; e.preventDefault(); e.dataTransfer.dropEffect = "copy"; });
  window.addEventListener("dragleave", () => { dragDepth = Math.max(0, dragDepth - 1); if (!dragDepth) document.body.classList.remove("dragging"); });
  window.addEventListener("drop", (e) => {
    e.preventDefault();
    dragDepth = 0;
    document.body.classList.remove("dragging");
    const dropped = Array.from((e.dataTransfer && e.dataTransfer.files) || []);
    // pywebview exposes the real path as `pywebviewFullPath`; fall back to reading bytes.
    addEntries(dropped.map((file) => file.pywebviewFullPath
      ? { name: file.name, size: file.size, path: file.pywebviewFullPath }
      : { name: file.name, size: file.size, file }));
  });

  render();
})();
