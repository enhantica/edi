// The start page's intro, the same as the desktop app's (app/qml/Components/HomeIntro.qml; the owner,
// 2026-11-14): "Making diffraction data analysis easy" fades in and holds, the other words fade out,
// "easy" and "diffraction" move to their places in the logo ("easy" turning Regular on the way), and
// the mark rolls in from beyond the left edge and brakes hard. It plays while the app downloads and
// starts, in full on every load until it is disabled (the owner, 2026-11-17). If the app is ready first, the page
// fades out once the intro ends; if the intro ends first, the mark keeps turning as the splash does until the app is
// ready. Skip and Disable are always shown: Skip is disabled until the app is ready and then fades the page out;
// Disable turns the intro off for later loads (the app's Preferences, Intro animation, read and write the same stored
// value) and leaves the splash alone. The app starts only once the intro's animations run (`ready`): a reload takes the
// app from the browser's cache and keeps the page busy at once, and animations not started by then stood still on
// their first frame, an empty page.
//
// Every motion is a Web Animations transform or opacity, so the browser's compositor keeps drawing it
// while the page's main thread is busy starting the app (see make_logo.py). A page driven by a test
// tool, opened with ?intro=0, or asking for reduced motion shows the splash only.
(() => {
  "use strict";
  const KEY = "edi.introAnimation";
  const loading = document.getElementById("loading");
  const splash = document.getElementById("splash");
  const status = document.getElementById("status");
  let loaded = false;
  let ended = false;
  let leaving = false;
  let layer = null;
  let skip = null;
  const animations = [];
  const outExpo = "cubic-bezier(0.16, 1, 0.3, 1)";

  function stored() {
    try {
      return localStorage.getItem(KEY) !== "off";
    } catch (e) {
      return true;
    }
  }
  function store(on) {
    try {
      if (on) localStorage.removeItem(KEY);
      else localStorage.setItem(KEY, "off");
    } catch (e) {
      // no storage: the choice lasts for this page only
    }
  }

  // The app is shown under the page, which fades out over a second.
  function reveal() {
    if (leaving) return;
    leaving = true;
    loading.style.pointerEvents = "none";
    const fade = loading.animate([{ opacity: 1 }, { opacity: 0 }], { duration: 1000, easing: outExpo, fill: "forwards" });
    fade.onfinish = () => {
      loading.style.display = "none";
    };
  }

  // Back to the splash as it was before the intro: the turning mark and the status line.
  function toSplash() {
    animations.forEach((animation) => animation.cancel());
    if (layer !== null) layer.remove();
    layer = null;
    splash.style.visibility = "";
    status.style.visibility = "";
    const mark = splash.querySelector(".mark");
    mark.style.animation = "none";
    void mark.offsetWidth;  // restart the turn from the angle the intro's mark ended at
    mark.style.animation = "";
  }

  const wanted =
    stored() && !navigator.webdriver && new URLSearchParams(location.search).get("intro") !== "0" &&
    !matchMedia("(prefers-reduced-motion: reduce)").matches && window.ediIntroWords !== undefined;

  window.ediIntro = {
    // The app has started: shown at once without the intro, else when the intro has ended.
    appLoaded(show) {
      loaded = true;
      show();
      if (!wanted || layer === null) {
        loading.style.display = "none";
        return;
      }
      if (skip !== null) skip.disabled = false;
      if (ended) reveal();
    },
    // The page shows a message instead of the app: no intro over it.
    abort() {
      if (layer !== null) toSplash();
    },
    // Settles once the intro's animations are running and a frame has been drawn (at once without the intro), so
    // the app's start, which keeps the page busy, cannot hold them on their first frame.
    ready: Promise.resolve(),
  };
  if (!wanted) return;

  const data = window.ediIntroWords;
  const box = splash.getBoundingClientRect();
  const page = loading.getBoundingClientRect();
  const scale = box.width / data.width;  // px per logo unit
  layer = document.createElement("div");
  layer.className = "intro";
  loading.appendChild(layer);
  loading.classList.add("introducing");
  splash.style.visibility = "hidden";
  status.style.visibility = "hidden";

  // A word as an outline, its baseline at (x, y) in the page.
  function word(key, x, y) {
    const shape = data.words[key];
    const height = data.ascent + data.descent;
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("viewBox", `0 ${-data.ascent} ${shape.advance} ${height}`);
    svg.setAttribute("width", shape.advance * scale);
    svg.setAttribute("height", height * scale);
    svg.style.left = `${x}px`;
    svg.style.top = `${y - data.ascent * scale}px`;
    svg.style.opacity = "0";
    const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
    path.setAttribute("d", shape.d);
    svg.appendChild(path);
    layer.appendChild(svg);
    return svg;
  }
  // A later animation of a property an earlier one also sets holds only after it starts ("forwards"), so it does not
  // override the earlier one before then.
  function play(element, keyframes, start, duration, easing = "linear", fill = "both") {
    const animation = element.animate(keyframes, { delay: start, duration, easing, fill });
    animations.push(animation);
    return animation;
  }

  // The tagline, centred on the page, "easy" laid out in SemiBold.
  const w = data.words;
  const lineWidth = (w.making.advance + w.diffraction.advance + w.middle.advance + w.easyBold.advance) * scale;
  const baseline = page.top + page.height / 2;
  let x = page.left + (page.width - lineWidth) / 2;
  const making = word("making", x, baseline);
  x += w.making.advance * scale;
  const diffraction = word("diffraction", x, baseline);
  const diffractionX = x;
  x += w.diffraction.advance * scale;
  const middle = word("middle", x, baseline);
  x += w.middle.advance * scale;
  const easyBold = word("easyBold", x, baseline);
  const easy = word("easy", x, baseline);
  const easyX = x;

  // The timing of HomeIntro.qml: a 1 s pause, a 1.5 s fade-in, a 2.5 s hold, a 2 s fade of the other
  // words, then the 1 s move with the mark's 1.2 s roll starting with it.
  const shown = [{ opacity: 0 }, { opacity: 1 }];
  for (const element of [making, diffraction, middle, easyBold]) play(element, shown, 1000, 1500);
  for (const element of [making, middle]) play(element, [{ opacity: 1 }, { opacity: 0 }], 5000, 2000, "linear", "forwards");
  const moveTo = (fromX, toX, toY) => [
    { transform: "translate(0, 0)" },
    { transform: `translate(${toX - fromX}px, ${toY - baseline}px)` },
  ];
  const easyEnd = [box.left + data.nameX * scale, box.top + data.baselines.easy * scale];
  const diffractionEnd = [box.left + data.nameX * scale, box.top + data.baselines.diffraction * scale];
  play(diffraction, moveTo(diffractionX, ...diffractionEnd), 7000, 1000, outExpo);
  play(easyBold, moveTo(easyX, ...easyEnd), 7000, 1000, outExpo);
  play(easy, moveTo(easyX, ...easyEnd), 7000, 1000, outExpo);
  // "easy" turns Regular over the middle of the move, as on the desktop: from 0.2 to 0.8 of the move's out-expo
  // progress, which it reaches 32 ms and 232 ms after the move starts.
  const lightAt = (t) => Math.min(1, Math.max(0, (1 - Math.pow(2, -10 * t) - 0.2) / 0.6));
  const light = [];
  for (let i = 0; i <= 20; ++i) light.push(lightAt(0.0322 + (0.2322 - 0.0322) * i / 20));
  play(easyBold, light.map((value, i) => ({ offset: i / 20, opacity: 1 - value })), 7032, 200, "linear", "forwards");
  play(easy, light.map((value, i) => ({ offset: i / 20, opacity: value })), 7032, 200);

  // The mark rolls without slipping, quartic ease-out: its turn is the distance over its radius. Before the roll it
  // waits beyond the left edge, where the roll's first frame holds it.
  const markSize = data.frame * scale;
  const mark = document.createElement("div");
  mark.className = "intro-mark";
  mark.style.width = `${markSize}px`;
  mark.style.height = `${markSize}px`;
  mark.style.left = `${box.left}px`;
  mark.style.top = `${box.top}px`;
  const markImage = document.createElement("img");
  markImage.src = splash.querySelector(".mark").src;
  markImage.alt = "";
  mark.appendChild(markImage);
  layer.appendChild(mark);
  const distance = box.left + markSize * 1.2;
  const roll = [];
  for (let i = 0; i <= 60; ++i) {
    const left = Math.pow(1 - i / 60, 4) * distance;  // still to go
    roll.push({ offset: i / 60, transform: `translate(${-left}px, 0) rotate(${(-left / (markSize / 2)) * (180 / Math.PI)}deg)` });
  }
  // The intro ends when the roll has finished on the animations' own clock, which starts with the first frame drawn
  // and so can lag a timer started now.
  play(mark, roll, 7000, 1200).finished.then(() => {
    ended = true;
    if (loaded) reveal();
    else toSplash();
  }, () => {});

  // Skip (once the app is ready) and Disable, text buttons at the bottom. Their gap to the page's edge
  // equals the space between them.
  const buttons = document.createElement("div");
  buttons.className = "intro-buttons";
  skip = document.createElement("button");
  skip.textContent = "Skip";
  skip.disabled = !loaded;
  skip.onclick = () => reveal();
  const disable = document.createElement("button");
  disable.textContent = "Disable";
  disable.onclick = () => {
    store(false);
    if (loaded) reveal();
    else toSplash();
  };
  buttons.append(skip, disable);
  layer.appendChild(buttons);

  const frame = () => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve)));
  window.ediIntro.ready = Promise.all(animations.map((animation) => animation.ready)).then(frame, frame);
})();
