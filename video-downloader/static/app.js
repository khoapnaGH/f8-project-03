/* VidGrab front-end */
(() => {
  "use strict";

  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  const PF = {
    youtube: { name: "YouTube", color: "#ff3b3b", icon: $(".pf-youtube svg").outerHTML },
    facebook: { name: "Facebook", color: "#2d88ff", icon: $(".pf-facebook svg").outerHTML },
    instagram: { name: "Instagram", color: "#e1306c", icon: $(".pf-instagram svg").outerHTML },
    tiktok: { name: "TikTok", color: "#111", icon: $(".pf-tiktok svg").outerHTML },
    other: { name: "Web", color: "#7c5cff", icon: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3a14 14 0 0 1 0 18M12 3a14 14 0 0 0 0 18"/></svg>' },
  };

  const ICON = {
    play: '<svg viewBox="0 0 24 24"><path d="m7 4 13 8-13 8z"/></svg>',
    download: '<svg viewBox="0 0 24 24"><path d="M12 4v11m0 0-4.5-4.5M12 15l4.5-4.5M5 20h14"/></svg>',
    folder: '<svg viewBox="0 0 24 24"><path d="M3 7a2 2 0 0 1 2-2h4l2 2h8a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg>',
    x: '<svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6 6 18"/></svg>',
    stop: '<svg viewBox="0 0 24 24"><rect x="6" y="6" width="12" height="12" rx="2"/></svg>',
    retry: '<svg viewBox="0 0 24 24"><path d="M3 12a9 9 0 1 0 3-6.7L3 8M3 3v5h5"/></svg>',
    trash: '<svg viewBox="0 0 24 24"><path d="M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14"/></svg>',
    eye: '<svg viewBox="0 0 24 24"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></svg>',
    text: '<svg viewBox="0 0 24 24"><path d="M4 6h16M4 12h16M4 18h10"/></svg>',
    video: '<svg viewBox="0 0 24 24"><rect x="2" y="5" width="15" height="14" rx="2"/><path d="m17 10 5-3v10l-5-3"/></svg>',
    audio: '<svg viewBox="0 0 24 24"><path d="M9 18V5l12-2v13"/><circle cx="6" cy="18" r="3"/><circle cx="18" cy="16" r="3"/></svg>',
    subtitle: '<svg viewBox="0 0 24 24"><rect x="2" y="5" width="20" height="14" rx="2"/><path d="M7 12h4M13 12h4M7 15h10"/></svg>',
    image: '<svg viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="9" cy="9" r="2"/><path d="m21 15-5-5L5 21"/></svg>',
    other: '<svg viewBox="0 0 24 24"><path d="M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9z"/><path d="M14 3v6h6"/></svg>',
    clock: '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></svg>',
    views: '<svg viewBox="0 0 24 24"><path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></svg>',
    heart: '<svg viewBox="0 0 24 24"><path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1-1.1a5.5 5.5 0 0 0-7.8 7.8L12 21l8.8-8.6a5.5 5.5 0 0 0 0-7.8z"/></svg>',
    cal: '<svg viewBox="0 0 24 24"><rect x="3" y="4" width="18" height="18" rx="2"/><path d="M16 2v4M8 2v4M3 10h18"/></svg>',
  };

  const state = {
    info: null,
    quality: "best",
    selectedSubs: new Map(), // key code|auto -> {code, auto}
    subShowAll: false,
    jobs: [],
    jobFilter: "all",
    settings: null,
    batchMode: "video",
    selectedEntries: new Set(),
    lastJobsSig: "",
  };

  /* ------------------------------------------------------------ utils */
  async function api(path, opts = {}) {
    const res = await fetch(path, {
      headers: opts.body && !(opts.body instanceof FormData) ? { "Content-Type": "application/json" } : {},
      ...opts,
      body: opts.body && !(opts.body instanceof FormData) ? JSON.stringify(opts.body) : opts.body,
    });
    let data = {};
    try { data = await res.json(); } catch { /* ignore */ }
    if (!res.ok) throw new Error(data.error || data.message || `Lỗi ${res.status}`);
    return data;
  }

  function toast(msg, type = "info", ms = 3800) {
    const el = document.createElement("div");
    el.className = `toast ${type}`;
    el.innerHTML = `<div>${esc(msg).replace(/\n/g, "<br>")}</div>`;
    $("#toasts").appendChild(el);
    setTimeout(() => { el.classList.add("out"); setTimeout(() => el.remove(), 260); }, ms);
  }

  const fmtDur = (s) => {
    if (!s && s !== 0) return "";
    s = Math.round(s);
    const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60;
    return h ? `${h}:${String(m).padStart(2, "0")}:${String(sec).padStart(2, "0")}` : `${m}:${String(sec).padStart(2, "0")}`;
  };
  const fmtNum = (n) => {
    if (n == null) return "";
    if (n >= 1e9) return (n / 1e9).toFixed(1).replace(/\.0$/, "") + " tỷ";
    if (n >= 1e6) return (n / 1e6).toFixed(1).replace(/\.0$/, "") + " tr";
    if (n >= 1e3) return (n / 1e3).toFixed(1).replace(/\.0$/, "") + "K";
    return String(n);
  };
  const fmtDate = (d) => (d && d.length === 8 ? `${d.slice(6)}/${d.slice(4, 6)}/${d.slice(0, 4)}` : "");
  const thumbUrl = (u) => (u ? `/api/thumb?url=${encodeURIComponent(u)}` : "");
  const fileUrl = (p, dl) => `/api/file?path=${encodeURIComponent(p)}${dl ? "&dl=1" : ""}`;

  function detectPlatform(url) {
    try {
      const h = new URL(url).hostname;
      if (/youtube\.com|youtu\.be/.test(h)) return "youtube";
      if (/facebook\.com|fb\.watch|fb\.com/.test(h)) return "facebook";
      if (/instagram\.com|instagr\.am/.test(h)) return "instagram";
      if (/tiktok\.com/.test(h)) return "tiktok";
      return "other";
    } catch { return null; }
  }
  const extractUrl = (t) => ((t || "").match(/https?:\/\/[^\s<>"']+/) || [""])[0].replace(/[).,;!]+$/, "");

  function heightLabel(h) {
    if (h >= 4320) return ["8K", "4320p"];
    if (h >= 2160) return ["4K", "2160p"];
    if (h >= 1440) return ["2K", "1440p"];
    if (h >= 1080) return ["Full HD", "1080p"];
    if (h >= 720) return ["HD", "720p"];
    return [`${h}p`, "SD"];
  }

  /* ------------------------------------------------------------ theme */
  const savedTheme = localStorage.getItem("vg-theme");
  if (savedTheme) document.documentElement.dataset.theme = savedTheme;
  $("#btnTheme").onclick = () => {
    const t = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    document.documentElement.dataset.theme = t;
    localStorage.setItem("vg-theme", t);
  };

  /* ------------------------------------------------------------ input */
  const urlInput = $("#urlInput");
  $$(".seg-btn").forEach((b) => (b.onclick = () => {
    $$(".seg-btn").forEach((x) => x.classList.toggle("active", x === b));
    $("#formSingle").classList.toggle("hidden", b.dataset.input !== "single");
    $("#formBatch").classList.toggle("hidden", b.dataset.input !== "batch");
    (b.dataset.input === "single" ? urlInput : $("#batchInput")).focus();
  }));

  function updateDetected() {
    const el = $("#detected");
    const p = detectPlatform(extractUrl(urlInput.value));
    if (!p) { el.className = "detected"; return; }
    el.textContent = PF[p].name;
    el.style.background = PF[p].color + "26";
    el.style.color = p === "tiktok" ? "var(--text)" : PF[p].color;
    el.className = "detected show";
  }
  urlInput.addEventListener("input", updateDetected);

  $("#btnPaste").onclick = async () => {
    try {
      const t = await navigator.clipboard.readText();
      if (!t) return toast("Clipboard trống", "warn");
      urlInput.value = extractUrl(t) || t.trim();
      updateDetected();
      analyze();
    } catch {
      urlInput.focus();
      toast("Trình duyệt chặn đọc clipboard — hãy nhấn Ctrl+V vào ô nhập.", "warn");
    }
  };

  // paste anywhere -> analyze
  document.addEventListener("paste", (e) => {
    const tag = (e.target.tagName || "").toLowerCase();
    if ((tag === "input" || tag === "textarea") && e.target !== urlInput) return;
    const text = e.clipboardData.getData("text");
    const url = extractUrl(text);
    if (!url) return;
    e.preventDefault();
    if (!$("#formBatch").classList.contains("hidden")) return;
    urlInput.value = url;
    updateDetected();
    analyze();
  });

  $("#formSingle").onsubmit = (e) => { e.preventDefault(); analyze(); };

  // batch
  const batchInput = $("#batchInput");
  const batchUrls = () => batchInput.value.split(/\s+/).map(extractUrl).filter(Boolean);
  batchInput.addEventListener("input", () => ($("#batchCount").textContent = `${batchUrls().length} link`));
  chipGroup($("#batchMode"), (v) => (state.batchMode = v));
  $("#formBatch").onsubmit = async (e) => {
    e.preventDefault();
    const urls = [...new Set(batchUrls())];
    if (!urls.length) return toast("Chưa có link nào", "warn");
    const mode = state.batchMode;
    const options = { mode, use_cookies: $("#useCookies").checked, quality: "best", audio_format: "mp3", audio_quality: "192", prefer_mp4: true };
    options.is_playlist = true; // batch: bỏ qua mục lỗi trong danh sách
    if (mode === "subs") options.subs = { langs: ["vi", "en", "vi-orig", "en-orig"], manual: true, auto: true, format: "srt" };
    try {
      const r = await api("/api/download", { method: "POST", body: { urls, options } });
      toast(`Đã thêm ${r.jobs.length} lượt tải`, "ok");
      batchInput.value = "";
      $("#batchCount").textContent = "0 link";
      pollJobs(true);
      $(".downloads").scrollIntoView({ behavior: "smooth" });
    } catch (err) { toast(err.message, "err"); }
  };

  function chipGroup(el, onChange) {
    el.addEventListener("click", (e) => {
      const c = e.target.closest(".chip");
      if (!c) return;
      $$(".chip", el).forEach((x) => x.classList.toggle("active", x === c));
      onChange && onChange(c.dataset.v);
    });
  }
  const chipVal = (el) => $(".chip.active", el)?.dataset.v;

  /* ------------------------------------------------------------ analyze */
  let analyzing = false;
  async function analyze() {
    const url = extractUrl(urlInput.value) || urlInput.value.trim();
    if (!url) { urlInput.focus(); return toast("Hãy dán một link trước", "warn"); }
    if (analyzing) return;
    analyzing = true;
    const btn = $("#btnAnalyze");
    btn.classList.add("loading"); btn.disabled = true;
    $(".lbl", btn).textContent = "Đang phân tích…";
    $("#result").classList.add("hidden");
    $("#errorBox").classList.add("hidden");
    $("#skeleton").classList.remove("hidden");
    try {
      const info = await api("/api/info", { method: "POST", body: { url, use_cookies: $("#useCookies").checked } });
      renderInfo(info);
    } catch (err) {
      $("#errorText").textContent = err.message;
      $("#errorBox").classList.remove("hidden");
    } finally {
      analyzing = false;
      btn.classList.remove("loading"); btn.disabled = false;
      $(".lbl", btn).textContent = "Phân tích";
      $("#skeleton").classList.add("hidden");
    }
  }

  $("#errCookie").onclick = () => openSettings("cookies");
  $("#errGuide").onclick = () => openModal("#modalGuide");
  $("#errDirect").onclick = async () => {
    const url = extractUrl(urlInput.value);
    if (!url) return;
    await startDownload({ mode: "video", quality: "best", prefer_mp4: true }, { url, title: url });
    $("#errorBox").classList.add("hidden");
  };

  function renderInfo(info) {
    state.info = info;
    state.selectedSubs.clear();
    state.subShowAll = false;
    const pf = PF[info.platform] || PF.other;

    // media
    const img = $("#rThumb");
    const wrap = img.parentElement;
    wrap.classList.remove("portrait");
    img.onload = () => wrap.classList.toggle("portrait", img.naturalHeight > img.naturalWidth * 1.05);
    img.onerror = () => { img.removeAttribute("src"); };
    img.src = info.thumbnail ? thumbUrl(info.thumbnail) : "";
    $("#rPlatform").innerHTML = `${esc(pf.name)}${info.extractor && info.platform === "other" ? " · " + esc(info.extractor) : ""}`;
    $("#rPlatform").style.background = pf.color;
    $("#rDuration").textContent = info.is_playlist ? `${info.count || info.entries.length} mục` : fmtDur(info.duration);

    const stats = [];
    if (info.view_count != null) stats.push(`<span class="stat">${ICON.views}${fmtNum(info.view_count)} lượt xem</span>`);
    if (info.like_count != null) stats.push(`<span class="stat">${ICON.heart}${fmtNum(info.like_count)}</span>`);
    if (info.upload_date) stats.push(`<span class="stat">${ICON.cal}${fmtDate(info.upload_date)}</span>`);
    $("#rStats").innerHTML = stats.join("");

    $("#rTitle").textContent = info.title;
    $("#rTitle").title = info.title;
    const meta = [];
    if (info.uploader) meta.push(`<span>👤 ${esc(info.uploader)}</span>`);
    if (info.duration && !info.is_playlist) meta.push(`<span>⏱ ${fmtDur(info.duration)}</span>`);
    if (info.is_playlist) meta.push(`<span>📂 Danh sách / story: ${info.count || info.entries.length} mục</span>`);
    meta.push(`<a href="${esc(info.webpage_url)}" target="_blank" rel="noopener">Mở link gốc ↗</a>`);
    $("#rMeta").innerHTML = meta.join("");

    renderQualities(info);
    renderSubs();
    renderEntries(info);

    $("#openThumb").href = info.thumbnail || "#";
    $("#openThumb").classList.toggle("hidden", !info.thumbnail);

    const hasSubs = info.subtitles.length + info.auto_subtitles.length > 0;
    $("#subCount").textContent = info.subtitles.length + info.auto_subtitles.length;
    $("#optSubWrap").classList.toggle("disabled", !hasSubs);

    $("#tabList").classList.toggle("hidden", !info.is_playlist);
    selectTab(info.is_playlist && !info.heights.length ? "list" : "video");
    $("#result").classList.remove("hidden");
    $("#result").scrollIntoView({ behavior: "smooth", block: "nearest" });
  }

  function renderQualities(info) {
    const grid = $("#qualityGrid");
    let hs = info.heights || [];
    hs = hs.map((h) => (typeof h === "number" ? { height: h, size: "" } : h));
    const items = [{ v: "best", top: "Tốt nhất", sub: "Tự động chọn cao nhất", tag: "★" }];
    const seen = new Set();
    hs.forEach((h) => {
      // gộp các độ phân giải lẻ (vd 1078p) về mốc gần nhất
      const std = [4320, 2160, 1440, 1080, 720, 480, 360, 240, 144].find((s) => h.height >= s * 0.9) || h.height;
      if (seen.has(std)) return;
      seen.add(std);
      const [top, sub] = heightLabel(std);
      items.push({ v: String(Math.max(h.height, std)), top: std >= 720 ? `${std}p` : top, sub: [std >= 720 ? top : sub, h.fps > 30 ? `${h.fps}fps` : "", h.size ? "~" + h.size : ""].filter(Boolean).join(" · ") });
    });
    if (!hs.length) {
      [1080, 720, 480].forEach((h) => items.push({ v: String(h), top: `${h}p`, sub: "Nếu có" }));
    }
    state.quality = "best";
    grid.innerHTML = items.map((it, i) => `
      <button class="qbtn ${i === 0 ? "active" : ""}" data-v="${it.v}">
        ${it.tag ? `<span class="tag">${it.tag}</span>` : ""}
        <b>${esc(it.top)}</b><small>${esc(it.sub)}</small>
      </button>`).join("");
    $("#qLabel").textContent = "";
  }
  $("#qualityGrid").addEventListener("click", (e) => {
    const b = e.target.closest(".qbtn");
    if (!b) return;
    $$(".qbtn", $("#qualityGrid")).forEach((x) => x.classList.toggle("active", x === b));
    state.quality = b.dataset.v;
    $("#qLabel").textContent = b.dataset.v === "best" ? "" : `· ${$("b", b).textContent}`;
  });

  /* tabs */
  function selectTab(name) {
    $$(".tabs .tab[data-tab]").forEach((t) => t.classList.toggle("active", t.dataset.tab === name));
    $$(".panel").forEach((p) => p.classList.toggle("active", p.dataset.panel === name));
  }
  $$(".tab[data-tab]").forEach((t) => (t.onclick = () => selectTab(t.dataset.tab)));

  /* ------------------------------------------------------------ subtitles */
  function renderSubs() {
    const info = state.info;
    if (!info) return;
    const q = $("#subSearch").value.trim().toLowerCase();
    const match = (s) => !q || s.code.toLowerCase().includes(q) || (s.name || "").toLowerCase().includes(q);
    const man = info.subtitles.filter(match);
    let auto = info.auto_subtitles.filter(match);
    const autoTotal = auto.length;
    const LIMIT = 12;
    if (!state.subShowAll && !q && auto.length > LIMIT) auto = auto.slice(0, LIMIT);

    const row = (s) => {
      const key = `${s.code}|${s.auto ? 1 : 0}`;
      const sel = state.selectedSubs.has(key);
      const orig = s.code.endsWith("-orig");
      return `<label class="sub-item ${sel ? "sel" : ""}" data-key="${esc(key)}" title="${esc(s.name)} (${esc(s.code)})">
        <span class="box"></span>
        <span class="nm">${esc(s.name)}</span>
        ${orig ? '<span class="orig">GỐC</span>' : `<span class="cd">${esc(s.code)}</span>`}
        <button type="button" class="eye" data-view="${esc(key)}" title="Xem nội dung">${ICON.eye}</button>
      </label>`;
    };
    $("#subManual").innerHTML = man.map(row).join("") || `<span class="muted small">Không có${q ? " kết quả" : ""}</span>`;
    $("#subAuto").innerHTML = auto.map(row).join("") || `<span class="muted small">Không có${q ? " kết quả" : ""}</span>`;
    $("#manCount").textContent = `${info.subtitles.length} ngôn ngữ`;
    $("#autoCount").textContent = `${info.auto_subtitles.length} ngôn ngữ`;
    $("#grpManual").classList.toggle("hidden", !info.subtitles.length);
    $("#grpAuto").classList.toggle("hidden", !info.auto_subtitles.length);
    $("#subMore").classList.toggle("hidden", state.subShowAll || !!q || autoTotal <= LIMIT);
    $("#subMore").textContent = `Hiện tất cả ${autoTotal} ngôn ngữ`;
    const none = !info.subtitles.length && !info.auto_subtitles.length;
    $("#subsEmpty").classList.toggle("hidden", !none);
    $("#subsWrap").classList.toggle("hidden", none);
    updateSubSel();
  }
  function updateSubSel() {
    const n = state.selectedSubs.size;
    $("#subSelInfo").textContent = n ? `Đã chọn ${n} ngôn ngữ: ${[...state.selectedSubs.values()].map((s) => s.code).join(", ")}` : "Chưa chọn ngôn ngữ nào";
    $("#dlSubs").disabled = !n;
    if (n && !$("#optSubs").dataset.touched) $("#optSubs").checked = true;
  }
  $("#subSearch").addEventListener("input", renderSubs);
  $("#subMore").onclick = () => { state.subShowAll = true; renderSubs(); };
  $("#optSubs").addEventListener("change", (e) => (e.target.dataset.touched = "1"));
  ["#subManual", "#subAuto"].forEach((id) => $(id).addEventListener("click", (e) => {
    const eye = e.target.closest("[data-view]");
    if (eye) {
      e.preventDefault(); e.stopPropagation();
      const [code, auto] = eye.dataset.view.split("|");
      viewTranscript(code, auto === "1");
      return;
    }
    const item = e.target.closest(".sub-item");
    if (!item) return;
    e.preventDefault();
    const key = item.dataset.key;
    const [code, auto] = key.split("|");
    if (state.selectedSubs.has(key)) state.selectedSubs.delete(key);
    else state.selectedSubs.set(key, { code, auto: auto === "1" });
    item.classList.toggle("sel");
    updateSubSel();
  }));
  chipGroup($("#subFmt"));

  function subsPayload() {
    const sel = [...state.selectedSubs.values()];
    return {
      langs: [...new Set(sel.map((s) => s.code))],
      manual: sel.some((s) => !s.auto),
      auto: sel.some((s) => s.auto),
      format: chipVal($("#subFmt")) || "srt",
    };
  }

  async function viewTranscript(code, auto) {
    const name = [...state.info.subtitles, ...state.info.auto_subtitles].find((s) => s.code === code && s.auto === auto)?.name || code;
    openPreview(`Phụ đề · ${name}`, '<div class="loading-box"><span class="spinner"></span>Đang lấy phụ đề…</div>');
    try {
      const r = await api("/api/transcript", { method: "POST", body: { url: state.info.webpage_url || state.info.url, lang: code, auto, use_cookies: $("#useCookies").checked } });
      showTranscript(r.segments, `${state.info.title} - ${code}`);
    } catch (err) {
      $("#pvBody").innerHTML = `<div class="error-box"><div class="err-icon">!</div><pre>${esc(err.message)}</pre></div>`;
    }
  }

  function showTranscript(segments, filename) {
    const body = $("#pvBody");
    if (!segments.length) { body.innerHTML = '<p class="muted">Phụ đề trống.</p>'; return; }
    body.innerHTML = `<div class="transcript ${$("#pvTime").checked ? "with-time" : ""}">${segments.map((s) => `<div class="seg"><span class="ts">${esc(s.start)}</span><span>${esc(s.text)}</span></div>`).join("")}</div>`;
    const textOf = () => segments.map((s) => ($("#pvTime").checked ? `[${s.start}] ` : "") + s.text).join("\n");
    ["#pvTimeWrap", "#pvCopy", "#pvSave"].forEach((id) => $(id).classList.remove("hidden"));
    $("#pvTime").onchange = () => $(".transcript", body)?.classList.toggle("with-time", $("#pvTime").checked);
    $("#pvCopy").onclick = async () => {
      try { await navigator.clipboard.writeText(textOf()); toast("Đã sao chép nội dung phụ đề", "ok"); }
      catch { toast("Không sao chép được", "err"); }
    };
    $("#pvSave").onclick = () => {
      const a = document.createElement("a");
      a.href = URL.createObjectURL(new Blob([textOf()], { type: "text/plain;charset=utf-8" }));
      a.download = (filename || "transcript").replace(/[\\/:*?"<>|]+/g, "_").slice(0, 120) + ".txt";
      a.click();
      setTimeout(() => URL.revokeObjectURL(a.href), 2000);
    };
  }

  /* ------------------------------------------------------------ playlist */
  function renderEntries(info) {
    state.selectedEntries = new Set(info.entries.map((e) => e.index));
    $("#listCount").textContent = info.count || info.entries.length;
    $("#entryList").innerHTML = info.entries.map((e) => `
      <div class="entry" data-i="${e.index}">
        <label class="check"><input type="checkbox" checked><span></span></label>
        <span class="idx">${e.index}</span>
        ${e.thumbnail ? `<img loading="lazy" src="${thumbUrl(e.thumbnail)}" onerror="this.style.visibility='hidden'">` : '<img alt="">'}
        <span class="et" title="${esc(e.title)}">${esc(e.title)}</span>
        <span class="ed">${fmtDur(e.duration)}</span>
      </div>`).join("");
    $("#selAll").checked = true;
    updateEntrySel();
  }
  function updateEntrySel() {
    const total = state.info?.entries.length || 0;
    $("#selInfo").textContent = `Đã chọn ${state.selectedEntries.size}/${total}`;
  }
  $("#entryList").addEventListener("click", (e) => {
    const row = e.target.closest(".entry");
    if (!row) return;
    e.preventDefault();
    const i = +row.dataset.i;
    const cb = $("input", row);
    if (state.selectedEntries.has(i)) state.selectedEntries.delete(i); else state.selectedEntries.add(i);
    cb.checked = state.selectedEntries.has(i);
    row.classList.toggle("off", !cb.checked);
    $("#selAll").checked = state.selectedEntries.size === state.info.entries.length;
    updateEntrySel();
  });
  $("#selAll").addEventListener("change", (e) => {
    const on = e.target.checked;
    state.selectedEntries = new Set(on ? state.info.entries.map((x) => x.index) : []);
    $$(".entry").forEach((r) => { $("input", r).checked = on; r.classList.toggle("off", !on); });
    updateEntrySel();
  });

  function playlistItems() {
    const info = state.info;
    if (!info?.is_playlist) return null;
    if (state.selectedEntries.size === info.entries.length && (info.count || 0) <= info.entries.length) return null;
    if (!state.selectedEntries.size) return "";
    // nén thành dạng 1-5,8,10-12
    const arr = [...state.selectedEntries].sort((a, b) => a - b);
    const parts = [];
    for (let i = 0; i < arr.length; i++) {
      let j = i;
      while (j + 1 < arr.length && arr[j + 1] === arr[j] + 1) j++;
      parts.push(i === j ? `${arr[i]}` : `${arr[i]}-${arr[j]}`);
      i = j;
    }
    return parts.join(",");
  }

  /* ------------------------------------------------------------ downloads */
  async function startDownload(options, override) {
    const info = state.info;
    const url = override?.url || info.webpage_url || info.url;
    const body = {
      url,
      options: {
        use_cookies: $("#useCookies").checked,
        title: override?.title ?? info?.title,
        thumbnail: override?.thumbnail ?? info?.thumbnail,
        ...options,
      },
    };
    if (!override && info?.is_playlist) {
      const items = playlistItems();
      if (items === "") return toast("Bạn chưa chọn mục nào trong danh sách", "warn");
      if (items) body.options.playlist_items = items;
      body.options.is_playlist = true;
    }
    try {
      await api("/api/download", { method: "POST", body });
      toast("Đã thêm vào danh sách tải ⬇", "ok", 2500);
      pollJobs(true);
    } catch (err) { toast(err.message, "err"); }
  }

  $("#dlVideo").onclick = () => {
    const withSubs = $("#optSubs").checked && state.selectedSubs.size;
    const subs = withSubs ? { ...subsPayload(), embed: $("#optEmbedSubs").checked } : null;
    if ($("#optEmbedSubs").checked && !withSubs) toast("Chưa chọn phụ đề để nhúng — hãy chọn ở tab Phụ đề.", "warn");
    startDownload({
      mode: "video",
      quality: state.quality,
      prefer_mp4: $("#optMp4").checked,
      h264: $("#optH264").checked,
      embed_metadata: $("#optMeta").checked,
      subs,
    });
  };
  $("#dlAudio").onclick = () => startDownload({
    mode: "audio",
    audio_format: chipVal($("#audioFmt")),
    audio_quality: chipVal($("#audioQ")),
    embed_thumbnail: $("#optCover").checked,
    embed_metadata: $("#optAMeta").checked,
  });
  chipGroup($("#audioFmt"), (v) => {
    const lossless = v === "wav" || v === "flac";
    $("#audioQ").style.opacity = lossless ? 0.4 : 1;
    $("#audioQ").style.pointerEvents = lossless ? "none" : "";
  });
  chipGroup($("#audioQ"));
  $("#dlSubs").onclick = () => {
    if (!state.selectedSubs.size) return toast("Hãy chọn ít nhất 1 ngôn ngữ", "warn");
    startDownload({ mode: "subs", subs: subsPayload() });
  };
  $("#dlThumb").onclick = () => startDownload({ mode: "thumbnail" });

  /* ------------------------------------------------------------ jobs */
  const STATUS = {
    queued: "Đang chờ", downloading: "Đang tải", processing: "Đang xử lý",
    done: "Hoàn tất", error: "Lỗi", cancelled: "Đã huỷ",
  };
  const MODE = { video: "VIDEO", audio: "AUDIO", subs: "PHỤ ĐỀ", thumbnail: "ẢNH" };
  const isActive = (j) => ["queued", "downloading", "processing"].includes(j.status);

  let pollTimer = null;
  async function pollJobs(force) {
    clearTimeout(pollTimer);
    try {
      const { jobs } = await api("/api/jobs");
      const prev = new Map(state.jobs.map((j) => [j.id, j.status]));
      jobs.forEach((j) => {
        const p = prev.get(j.id);
        if (p && p !== j.status) {
          if (j.status === "done") toast(`✅ Xong: ${j.title}`, "ok");
          if (j.status === "error") toast(`❌ Lỗi: ${j.title}`, "err");
        }
      });
      state.jobs = jobs;
      renderJobs();
    } catch { /* server offline */ }
    const active = state.jobs.some(isActive);
    pollTimer = setTimeout(pollJobs, active || force ? 800 : 3000);
  }

  function fileIcon(kind) { return ICON[kind] || ICON.other; }

  function jobHtml(j) {
    const pf = PF[j.platform] || PF.other;
    const pct = Math.max(0, Math.min(100, j.progress || 0));
    const indet = (j.status === "downloading" && !pct) || j.status === "processing" || j.status === "queued";
    const sub = [];
    sub.push(`<span class="st st-${j.status}">${STATUS[j.status] || j.status}</span>`);
    sub.push(`<span class="mode-tag">${MODE[j.mode] || j.mode}</span>`);
    if (j.status === "downloading") {
      if (pct) sub.push(`<span>${pct.toFixed(1)}%</span>`);
      if (j.downloaded) sub.push(`<span>${esc(j.downloaded)}${j.total ? " / " + esc(j.total) : ""}</span>`);
      if (j.speed) sub.push(`<span>⚡ ${esc(j.speed)}</span>`);
      if (j.eta) sub.push(`<span>⏳ ${esc(j.eta)}</span>`);
    }
    if (j.item) sub.push(`<span>📂 ${esc(j.item)}</span>`);
    if (j.status === "processing" && j.message) sub.push(`<span>${esc(j.message)}</span>`);
    if (j.status === "done" && j.message) sub.push(`<span class="muted">${esc(j.message)}</span>`);

    const files = (j.files || []).map((f) => {
      const canView = ["video", "audio", "image", "subtitle"].includes(f.kind);
      return `<span class="file-chip" title="${esc(f.path)}">${fileIcon(f.kind)}
        <span class="fn">${esc(f.name)}</span><span class="fs">${esc(f.size)}</span>
        ${canView ? `<button data-act="view" data-path="${esc(f.path)}" data-kind="${f.kind}" title="Xem">${f.kind === "subtitle" ? ICON.text : ICON.play}</button>` : ""}
        <a href="${fileUrl(f.path, true)}" title="Lưu về máy (qua trình duyệt)">${ICON.download}</a>
        <button data-act="reveal" data-path="${esc(f.path)}" title="Mở thư mục chứa file">${ICON.folder}</button>
      </span>`;
    }).join("");

    const actions = [];
    if (isActive(j)) actions.push(`<button class="icon-btn sm" data-act="cancel" title="Huỷ">${ICON.stop}</button>`);
    if (["error", "cancelled"].includes(j.status)) actions.push(`<button class="icon-btn sm" data-act="retry" title="Thử lại">${ICON.retry}</button>`);
    if (!isActive(j)) actions.push(`<button class="icon-btn sm" data-act="remove" title="Xoá khỏi danh sách">${ICON.x}</button>`);

    return `<div class="job ${j.status}" data-id="${j.id}">
      <div class="jt">${j.thumbnail ? `<img src="${thumbUrl(j.thumbnail)}" loading="lazy" onerror="this.remove()">` : ICON[j.mode === "audio" ? "audio" : j.mode === "subs" ? "subtitle" : "video"]}
        ${j.platform !== "other" ? `<span class="pfd">${pf.icon}</span>` : ""}</div>
      <div class="jm">
        <div class="jtitle" title="${esc(j.title)}">${esc(j.title)}</div>
        <div class="jsub">${sub.join("")}</div>
        ${isActive(j) ? `<div class="bar ${indet ? "indet" : ""} ${j.status === "processing" ? "processing" : ""}"><i style="width:${pct}%"></i></div>` : ""}
        ${j.status === "error" ? `<div class="jerr">${esc(j.error)}</div>` : ""}
        ${files ? `<div class="files">${files}</div>` : ""}
      </div>
      <div class="ja">${actions.join("")}</div>
    </div>`;
  }

  function renderJobs() {
    const f = state.jobFilter;
    const list = state.jobs.filter((j) =>
      f === "all" ? true : f === "active" ? isActive(j) : f === "done" ? j.status === "done" : ["error", "cancelled"].includes(j.status));
    const sig = JSON.stringify(list.map((j) => [j.id, j.status, j.progress, j.speed, j.eta, j.message, j.item, j.files.length, j.title, j.thumbnail]));
    const active = state.jobs.filter(isActive).length;
    const pill = $("#activeCount");
    pill.textContent = active ? `${active} đang chạy` : `${state.jobs.length} mục`;
    pill.classList.toggle("live", !!active);
    document.title = active ? `(${active}) Đang tải · VidGrab` : "VidGrab · Tải video, story & phụ đề";
    $("#jobEmpty").classList.toggle("hidden", list.length > 0);
    if (sig === state.lastJobsSig) return;
    state.lastJobsSig = sig;

    // cập nhật theo từng phần tử để không giật ảnh
    const box = $("#jobList");
    const existing = new Map($$(".job", box).map((el) => [el.dataset.id, el]));
    const frag = document.createDocumentFragment();
    list.forEach((j) => {
      const html = jobHtml(j);
      let el = existing.get(j.id);
      if (el && el.dataset.html === html) { frag.appendChild(el); return; }
      const tmp = document.createElement("div");
      tmp.innerHTML = html;
      const nel = tmp.firstElementChild;
      nel.dataset.html = html;
      if (el) {
        // giữ ảnh cũ để không nháy
        const oldImg = $(".jt img", el), newImg = $(".jt img", nel);
        if (oldImg && newImg && oldImg.src === newImg.src) newImg.replaceWith(oldImg);
        nel.style.animation = "none";
      }
      frag.appendChild(nel);
    });
    box.innerHTML = "";
    box.appendChild(frag);
  }

  chipGroup($("#jobFilter"), (v) => { state.jobFilter = v; state.lastJobsSig = ""; renderJobs(); });

  $("#jobList").addEventListener("click", async (e) => {
    const b = e.target.closest("[data-act]");
    if (!b) return;
    const id = b.closest(".job")?.dataset.id;
    const act = b.dataset.act;
    try {
      if (act === "cancel") { await api(`/api/jobs/${id}/cancel`, { method: "POST" }); toast("Đang huỷ…", "warn", 1500); }
      if (act === "retry") { await api(`/api/jobs/${id}/retry`, { method: "POST" }); }
      if (act === "remove") { await api(`/api/jobs/${id}`, { method: "DELETE" }); }
      if (act === "reveal") { await api("/api/open-folder", { method: "POST", body: { path: b.dataset.path } }); }
      if (act === "view") previewFile(b.dataset.path, b.dataset.kind);
      pollJobs(true);
    } catch (err) { toast(err.message, "err"); }
  });

  $("#btnClear").onclick = async () => { await api("/api/jobs/clear", { method: "POST" }); pollJobs(true); };
  $("#btnFolder").onclick = async () => {
    try { await api("/api/open-folder", { method: "POST", body: {} }); }
    catch (err) { toast(err.message, "err"); }
  };

  async function previewFile(path, kind) {
    const name = path.split("/").pop();
    const src = fileUrl(path);
    if (kind === "video") openPreview(name, `<video src="${src}" controls autoplay playsinline></video>`);
    else if (kind === "audio") openPreview(name, `<audio src="${src}" controls autoplay></audio>`);
    else if (kind === "image") openPreview(name, `<img src="${src}" alt="">`);
    else if (kind === "subtitle") {
      openPreview(name, '<div class="loading-box"><span class="spinner"></span>Đang đọc…</div>');
      try {
        const r = await api(`/api/file-text?path=${encodeURIComponent(path)}`);
        if (r.segments?.length) showTranscript(r.segments, name.replace(/\.[^.]+$/, ""));
        else $("#pvBody").innerHTML = `<div class="transcript-plain">${esc(r.text)}</div>`;
      } catch (err) { $("#pvBody").innerHTML = `<p>${esc(err.message)}</p>`; }
    }
  }

  /* ------------------------------------------------------------ modals */
  function openModal(id) { $(id).classList.add("open"); }
  function closeModal(m) {
    m.classList.remove("open");
    if (m.id === "modalPreview") {
      $("#pvBody").innerHTML = ""; // dừng video
      ["#pvTimeWrap", "#pvCopy", "#pvSave"].forEach((id) => $(id).classList.add("hidden"));
    }
  }
  function openPreview(title, html) {
    $("#pvTitle").textContent = title;
    $("#pvBody").innerHTML = html;
    ["#pvTimeWrap", "#pvCopy", "#pvSave"].forEach((id) => $(id).classList.add("hidden"));
    openModal("#modalPreview");
  }
  $$(".modal").forEach((m) => {
    m.addEventListener("mousedown", (e) => { if (e.target === m) closeModal(m); });
    $$("[data-close]", m).forEach((b) => (b.onclick = () => closeModal(m)));
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") $$(".modal.open").forEach(closeModal);
  });
  $("#btnGuide").onclick = () => openModal("#modalGuide");

  /* ------------------------------------------------------------ settings */
  const CK_PF = [
    { k: "facebook", name: "Facebook", hint: "Story, video nhóm kín, video bạn bè" },
    { k: "instagram", name: "Instagram", hint: "Story, highlight, tài khoản private" },
    { k: "tiktok", name: "TikTok", hint: "Tài khoản private, video giới hạn tuổi" },
    { k: "youtube", name: "YouTube", hint: "Video không công khai, thành viên, giới hạn tuổi" },
    { k: "all", name: "Tất cả (chung)", hint: "Một file chứa cookie nhiều trang" },
  ];

  async function loadSettings() {
    const s = await api("/api/settings");
    state.settings = s;
    renderSettings();
    return s;
  }

  function renderSettings() {
    const s = state.settings;
    if (!s) return;
    $("#cookieGrid").innerHTML = CK_PF.map((p) => {
      const c = s.cookies[p.k] || {};
      const icon = PF[p.k]?.icon || '<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/></svg>';
      return `<div class="ck ${c.exists ? "has" : ""}" data-pf="${p.k}">
        <div class="ck-top" style="color:${PF[p.k]?.color && p.k !== "tiktok" ? PF[p.k].color : "var(--text)"}">${icon}<span style="color:var(--text)">${p.name}</span></div>
        <div class="ck-st">${c.exists ? `✔ Đã nạp · ${c.size} · ${c.updated}` : esc(p.hint)}</div>
        <div class="ck-act">
          <button class="btn btn-ghost btn-sm" data-ck="upload">${c.exists ? "Thay file" : "Nạp file"}</button>
          <button class="btn btn-ghost btn-sm" data-ck="paste">Dán nội dung</button>
          ${c.exists ? '<button class="btn btn-ghost btn-sm btn-danger" data-ck="delete">Xoá</button>' : ""}
        </div>
        <input type="file" accept=".txt,.json,text/plain,application/json" hidden>
      </div>`;
    }).join("");

    const sel = $("#setBrowser");
    sel.innerHTML = `<option value="">— Không dùng —</option>` + s.browsers.map((b) => `<option value="${b}">${b[0].toUpperCase() + b.slice(1)}</option>`).join("");
    sel.value = s.settings.cookie_browser || "";
    $("#setDir").value = s.settings.download_dir;
    $("#setTmpl").value = s.settings.filename_template;
    $("#setConc").value = s.settings.max_concurrent;
    $("#setPerPf").checked = !!s.settings.folder_per_platform;

    const any = Object.values(s.cookies).some((c) => c.exists) || !!s.settings.cookie_browser;
    $("#cookieDot").classList.toggle("on", any);

    $("#sysInfo").innerHTML = [
      ["yt-dlp", s.ytdlp_version, true],
      ["ffmpeg", s.ffmpeg || "Chưa cài — không ghép được video HD / MP3", !!s.ffmpeg],
      ["JS runtime (deno/node — YouTube cần)", s.js_runtime ? "Có" : "Chưa có — nên cài Deno", s.js_runtime],
      ["Python / Hệ điều hành", `${s.python} · ${s.os}`, true],
    ].map(([k, v, ok]) => `<div class="sys"><div class="k">${k}</div><div class="v ${ok ? "ok" : "bad"}">${esc(v)}</div></div>`).join("");
    $("#footVer").textContent = `yt-dlp ${s.ytdlp_version}`;
    if (!s.ffmpeg && !sessionStorage.getItem("ffwarn")) {
      sessionStorage.setItem("ffwarn", 1);
      toast("Chưa tìm thấy ffmpeg — video chất lượng cao & MP3 cần ffmpeg. Xem README để cài.", "warn", 8000);
    }
  }

  async function uploadCookie(pf, fileOrText) {
    try {
      let r;
      if (typeof fileOrText === "string") r = await api(`/api/cookies/${pf}`, { method: "POST", body: { content: fileOrText } });
      else { const fd = new FormData(); fd.append("file", fileOrText); r = await api(`/api/cookies/${pf}`, { method: "POST", body: fd }); }
      state.settings = r;
      renderSettings();
      toast(`Đã nạp cookie ${CK_PF.find((p) => p.k === pf)?.name}`, "ok");
    } catch (err) { toast(err.message, "err", 6000); }
  }

  $("#cookieGrid").addEventListener("click", async (e) => {
    const b = e.target.closest("[data-ck]");
    if (!b) return;
    const card = b.closest(".ck");
    const pf = card.dataset.pf;
    if (b.dataset.ck === "upload") $("input[type=file]", card).click();
    if (b.dataset.ck === "delete") {
      if (!confirm("Xoá cookie này?")) return;
      state.settings = await api(`/api/cookies/${pf}`, { method: "DELETE" });
      renderSettings();
    }
    if (b.dataset.ck === "paste") {
      let ta = $("textarea", card);
      if (ta) { if (ta.value.trim()) uploadCookie(pf, ta.value); else ta.remove(); return; }
      ta = document.createElement("textarea");
      ta.placeholder = "Dán nội dung cookies.txt hoặc JSON rồi bấm 'Dán nội dung' lần nữa để lưu";
      card.insertBefore(ta, $(".ck-act", card));
      ta.focus();
    }
  });
  $("#cookieGrid").addEventListener("change", (e) => {
    if (e.target.type !== "file") return;
    const f = e.target.files[0];
    if (f) uploadCookie(e.target.closest(".ck").dataset.pf, f);
  });
  // kéo thả file vào ô cookie
  $("#cookieGrid").addEventListener("dragover", (e) => { const c = e.target.closest(".ck"); if (c) { e.preventDefault(); e.stopPropagation(); c.classList.add("drag"); } });
  $("#cookieGrid").addEventListener("dragleave", (e) => e.target.closest(".ck")?.classList.remove("drag"));
  $("#cookieGrid").addEventListener("drop", (e) => {
    const c = e.target.closest(".ck");
    if (!c) return;
    e.preventDefault(); e.stopPropagation();
    c.classList.remove("drag");
    const f = e.dataTransfer.files[0];
    if (f) uploadCookie(c.dataset.pf, f);
  });

  function openSettings(tab = "cookies") {
    selectSTab(tab);
    loadSettings().catch(() => {});
    openModal("#modalSettings");
  }
  function selectSTab(name) {
    $$("[data-stab]").forEach((t) => t.classList.toggle("active", t.dataset.stab === name));
    $$(".spanel").forEach((p) => p.classList.toggle("active", p.dataset.spanel === name));
  }
  $$("[data-stab]").forEach((t) => (t.onclick = () => selectSTab(t.dataset.stab)));
  $("#btnSettings").onclick = () => openSettings();

  $("#btnSaveSettings").onclick = async () => {
    try {
      state.settings = await api("/api/settings", {
        method: "POST",
        body: {
          download_dir: $("#setDir").value.trim(),
          filename_template: $("#setTmpl").value.trim(),
          max_concurrent: +$("#setConc").value || 3,
          folder_per_platform: $("#setPerPf").checked,
          cookie_browser: $("#setBrowser").value,
        },
      });
      renderSettings();
      toast("Đã lưu cài đặt", "ok");
      closeModal($("#modalSettings"));
    } catch (err) { toast(err.message, "err"); }
  };

  $("#btnUpdate").onclick = async () => {
    const b = $("#btnUpdate");
    b.disabled = true;
    b.lastChild.textContent = " Đang cập nhật…";
    const out = $("#updateOut");
    out.classList.remove("hidden");
    out.textContent = "Đang chạy pip install -U yt-dlp …";
    try {
      const r = await api("/api/update-ytdlp", { method: "POST" });
      out.textContent = `${r.message}\n\n${r.output || ""}`;
      toast(r.message, r.ok ? "ok" : "err", 6000);
    } catch (err) { out.textContent = err.message; }
    b.disabled = false;
    b.lastChild.textContent = " Cập nhật yt-dlp";
  };

  /* ------------------------------------------------------------ drag & drop global */
  let dragDepth = 0;
  window.addEventListener("dragenter", (e) => {
    if ($("#modalSettings").classList.contains("open")) return;
    dragDepth++; $("#dropOverlay").classList.add("show"); e.preventDefault();
  });
  window.addEventListener("dragleave", () => { if (--dragDepth <= 0) { dragDepth = 0; $("#dropOverlay").classList.remove("show"); } });
  window.addEventListener("dragover", (e) => e.preventDefault());
  window.addEventListener("drop", (e) => {
    e.preventDefault();
    dragDepth = 0;
    $("#dropOverlay").classList.remove("show");
    if ($("#modalSettings").classList.contains("open")) return;
    const f = e.dataTransfer.files[0];
    if (f && /\.(txt|json)$/i.test(f.name)) {
      openSettings("cookies");
      toast("Hãy thả file cookie vào đúng ô nền tảng", "info");
      return;
    }
    const text = e.dataTransfer.getData("text/uri-list") || e.dataTransfer.getData("text");
    const url = extractUrl(text);
    if (url) { urlInput.value = url; updateDetected(); analyze(); }
  });

  /* ------------------------------------------------------------ init */
  loadSettings().catch(() => toast("Không kết nối được máy chủ VidGrab. Hãy chạy app.py", "err", 8000));
  pollJobs();
  urlInput.focus();
  const qs = new URLSearchParams(location.search).get("url");
  if (qs) { urlInput.value = qs; updateDetected(); analyze(); }
})();
