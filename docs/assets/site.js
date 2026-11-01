/* 60 Sekunden Wissen – Homepage: Film, Video-Raster, Player-Fenster, Hinweise. */
(() => {
  "use strict";
  const $ = (s, el = document) => el.querySelector(s);
  const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const NICHE_COLOR = {
    Autos: "var(--c-autos)", Psychologie: "var(--c-psychologie)", Geschichte: "var(--c-geschichte)",
    Geld: "var(--c-geld)", Geografie: "var(--c-geografie)",
  };
  const nf = new Intl.NumberFormat("de-DE");
  const compact = new Intl.NumberFormat("de-DE", { notation: "compact", maximumFractionDigits: 1 });
  const rtf = new Intl.RelativeTimeFormat("de", { numeric: "auto" });

  /* ---------- Hinweis (Toast) ---------- */
  let toastTimer;
  function toast(text, ok = true) {
    const el = $("#toast");
    // Ein offenes Fenster liegt in der obersten Ebene: der Hinweis muss mit hinein.
    const host = $("#sheet").open ? $("#sheet") : document.body;
    if (el.parentElement !== host) host.append(el);
    $("#toastText").textContent = text;
    $(".ok", el).toggleAttribute("hidden", !ok);
    el.classList.add("show");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => el.classList.remove("show"), 2200);
  }

  /* ---------- Einblenden beim Scrollen ---------- */
  const io = "IntersectionObserver" in window && !reduceMotion
    ? new IntersectionObserver((entries) => {
        for (const e of entries) if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); }
      }, { rootMargin: "0px 0px -8% 0px" })
    : null;
  function reveal(el) { io ? io.observe(el) : el.classList.add("in"); }
  document.querySelectorAll(".reveal").forEach(reveal);

  /* ---------- HyperFrames-Film im Hero ---------- */
  const film = $("#film");
  const toggle = $("#filmToggle");
  function setToggle(playing) {
    toggle.setAttribute("aria-label", playing ? "Film anhalten" : "Film abspielen");
    $(".i-pause", toggle).toggleAttribute("hidden", !playing);
    $(".i-play", toggle).toggleAttribute("hidden", playing);
  }
  if (film) {
    if (!reduceMotion) film.setAttribute("autoplay", "");
    setToggle(!reduceMotion);
    film.addEventListener("play", () => setToggle(true));
    film.addEventListener("pause", () => setToggle(false));
    film.addEventListener("error", () => { toggle.hidden = true; });
    toggle.addEventListener("click", () => {
      if (typeof film.play !== "function") return;
      film.paused ? film.play() : film.pause();
    });
    // Unsichtbar? Dann anhalten und Strom sparen.
    if ("IntersectionObserver" in window && !reduceMotion) {
      let userPaused = false;
      toggle.addEventListener("click", () => { userPaused = !film.paused; });
      new IntersectionObserver(([e]) => {
        if (typeof film.play !== "function" || !film.ready) return;
        if (!e.isIntersecting && !film.paused) film.pause();
        else if (e.isIntersecting && film.paused && !userPaused) film.play();
      }, { threshold: 0.2 }).observe(film);
    }
  }

  /* ---------- Video-Raster ---------- */
  const grid = $("#grid");
  let videos = [];
  let channelUrl = "https://www.youtube.com/@60SekundenWissen-s4i";
  let active = "";

  function ago(iso) {
    const diff = (new Date(iso) - Date.now()) / 1000;
    const steps = [["day", 86400], ["hour", 3600], ["minute", 60]];
    for (const [unit, s] of steps) if (Math.abs(diff) >= s || unit === "minute") return rtf.format(Math.round(diff / s), unit);
  }

  function card(v, i) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "vcard reveal";
    b.style.setProperty("--niche", NICHE_COLOR[v.niche] || "var(--ink-3)");
    b.style.transitionDelay = `${Math.min(i, 7) * 0.04}s`;
    b.setAttribute("aria-label", `${v.title}, ${nf.format(v.views)} Aufrufe. Video abspielen`);
    const thumb = document.createElement("div");
    thumb.className = "vthumb";
    if (v.thumb) {
      const img = new Image();
      img.src = v.thumb; img.alt = ""; img.loading = "lazy"; img.decoding = "async";
      img.onerror = () => img.replaceWith(placeholder(v));
      thumb.append(img);
    } else thumb.append(placeholder(v));
    thumb.insertAdjacentHTML("beforeend",
      `<span class="vplay" aria-hidden="true"><svg viewBox="0 0 16 16"><path d="M4 2.4v11.2a.8.8 0 0 0 1.2.7l9-5.6a.8.8 0 0 0 0-1.4l-9-5.6A.8.8 0 0 0 4 2.4z"/></svg></span>` +
      `<span class="vviews">${compact.format(v.views)} Aufrufe</span>`);
    const meta = document.createElement("div");
    meta.className = "vmeta";
    meta.innerHTML = `<span class="dot"></span>`;
    meta.append(`${v.niche} · ${ago(v.published)}`);
    const title = document.createElement("div");
    title.className = "vtitle";
    title.textContent = v.title;
    b.append(thumb, meta, title);
    b.addEventListener("click", () => openSheet(v, b));
    return b;
  }

  function placeholder(v) {
    const d = document.createElement("div");
    d.className = "ph";
    d.textContent = v.title;
    return d;
  }

  function render() {
    const list = videos.filter((v) => !active || v.niche === active);
    grid.classList.remove("skeleton");
    grid.removeAttribute("aria-busy");
    grid.replaceChildren();
    if (!list.length) {
      const e = document.createElement("p");
      e.className = "empty";
      e.textContent = videos.length ? `Unter den letzten Shorts ist gerade keiner zum Thema ${active}.` : "Gerade sind keine Videos geladen. Schau direkt auf YouTube vorbei.";
      grid.append(e);
      return;
    }
    list.forEach((v, i) => { const c = card(v, i); grid.append(c); reveal(c); });
  }

  fetch("videos.json", { cache: "no-cache" })
    .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
    .then((data) => {
      videos = (data.videos || []).filter((v) => /^[\w-]{11}$/.test(v.id));
      if (data.channel && data.channel.url) channelUrl = data.channel.url;
      const total = videos.reduce((s, v) => s + (v.views || 0), 0);
      $("#statViews").textContent = total >= 10000 ? compact.format(total) : nf.format(total);
      $("#statCount").textContent = videos.length;
      render();
    })
    .catch(() => { videos = []; render(); });

  /* Segmentierte Auswahl mit gleitendem Hintergrund */
  const seg = $("#filter");
  const segThumb = $(".thumb", seg);
  function moveThumb() {
    const b = $('button[aria-pressed="true"]', seg);
    segThumb.style.width = `${b.offsetWidth}px`;
    segThumb.style.transform = `translateX(${b.offsetLeft}px)`;
  }
  seg.addEventListener("click", (e) => {
    const b = e.target.closest("button");
    if (!b) return;
    seg.querySelectorAll("button").forEach((x) => x.setAttribute("aria-pressed", String(x === b)));
    active = b.dataset.niche;
    moveThumb();
    b.scrollIntoView({ block: "nearest", inline: "nearest", behavior: reduceMotion ? "auto" : "smooth" });
    render();
  });
  addEventListener("resize", moveThumb);
  (document.fonts ? document.fonts.ready : Promise.resolve()).then(moveThumb);
  moveThumb();

  /* ---------- Player-Fenster ---------- */
  const sheet = $("#sheet");
  let current = null;
  let opener = null;

  function openSheet(v, from) {
    current = v;
    opener = from;
    const url = `https://www.youtube.com/shorts/${v.id}`;
    // YouTube lädt erst nach dem Antippen, im datensparsamen Modus (youtube-nocookie.com).
    const frame = document.createElement("iframe");
    frame.src = `https://www.youtube-nocookie.com/embed/${v.id}?autoplay=1&playsinline=1&rel=0&modestbranding=1`;
    frame.title = v.title;
    frame.allow = "autoplay; encrypted-media; picture-in-picture; fullscreen";
    frame.referrerPolicy = "strict-origin-when-cross-origin";
    $("#sheetVideo").replaceChildren(frame);
    $("#sheetTitle").textContent = v.title;
    $("#sheetText").textContent = v.text || "";
    const meta = $("#sheetMeta");
    meta.style.setProperty("--niche", NICHE_COLOR[v.niche] || "var(--ink-3)");
    meta.innerHTML = `<span class="dot"></span>`;
    meta.append(`${v.niche} · ${nf.format(v.views)} Aufrufe · ${ago(v.published)}`);
    $("#sheetYt").href = url;
    if (film && typeof film.pause === "function" && !film.paused) film.pause();
    sheet.showModal();
    $("#sheetClose").focus();
  }

  function closeSheet() {
    sheet.close();
  }
  sheet.addEventListener("close", () => {
    $("#sheetVideo").replaceChildren();
    document.body.append($("#toast"));
    if (opener) opener.focus();
  });
  $("#sheetClose").addEventListener("click", closeSheet);
  sheet.addEventListener("click", (e) => { if (e.target === sheet) closeSheet(); });

  $("#sheetCopy").addEventListener("click", async () => {
    if (!current) return;
    const url = `https://www.youtube.com/shorts/${current.id}`;
    try {
      if (navigator.share && matchMedia("(pointer: coarse)").matches) {
        await navigator.share({ title: current.title, url });
        return;
      }
      await navigator.clipboard.writeText(url);
      toast("Link kopiert");
    } catch (err) {
      if (err && err.name === "AbortError") return;
      toast("Kopieren ging nicht. Link: youtube.com/shorts/" + current.id, false);
    }
  });

  /* Kleiner Hinweis, wenn ein YouTube-Link in neuem Tab aufgeht */
  document.querySelectorAll(".js-yt").forEach((a) => {
    a.target = "_blank";
    a.addEventListener("click", () => toast("YouTube öffnet sich in einem neuen Tab"));
  });
  $("#sheetYt").target = "_blank";
})();
