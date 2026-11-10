(() => {
  'use strict';
  if (window.__ediNetworkMount) { window.__ediNetworkMount(); return; }

  function createNetwork(root) {
    if (!root || root.__pulseController) return;
    const svg = root.querySelector('.network-linework');
    const toggle = root.querySelector('[data-pulse-toggle]');
    if (!svg) return;

    const NS = 'http://www.w3.org/2000/svg';
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    const viewBox = svg.viewBox.baseVal;
    const bounds = {
      left: viewBox.x, top: viewBox.y,
      right: viewBox.x + viewBox.width, bottom: viewBox.y + viewBox.height
    };
    const clamp = (v, a = 0, b = 1) => Math.max(a, Math.min(b, v));
    const random = (a, b) => a + Math.random() * (b - a);
    const ease = v => { const t = clamp(v); return t * t * (3 - 2 * t); };
    const interpolate = (a, b, t) => ({x: a.x + (b.x - a.x) * t, y: a.y + (b.y - a.y) * t});

    // Liang–Barsky clipping gives legal, visibly on-canvas starting positions.
    function visibleInterval(a, b, viewport = bounds) {
      const dx = b.x - a.x, dy = b.y - a.y;
      const ps = [-dx, dx, -dy, dy];
      const qs = [a.x - viewport.left, viewport.right - a.x, a.y - viewport.top, viewport.bottom - a.y];
      let lo = 0, hi = 1;
      for (let i = 0; i < 4; i++) {
        if (Math.abs(ps[i]) < 1e-9) {
          if (qs[i] < 0) return null;
        } else {
          const t = qs[i] / ps[i];
          if (ps[i] < 0) lo = Math.max(lo, t);
          else hi = Math.min(hi, t);
          if (lo > hi) return null;
        }
      }
      return [lo, hi];
    }

    function makeGraph(groupId) {
      const group = svg.querySelector('#' + groupId);
      if (!group) return null;
      const vertices = new Map();
      const edges = [];
      const seen = new Set();
      function vertex(x, y) {
        const key = x + ',' + y;
        if (!vertices.has(key)) vertices.set(key, {key, x, y, edges: []});
        return vertices.get(key);
      }
      for (const path of group.querySelectorAll('path[d]')) {
        const d = path.getAttribute('d');
        // The supplied artwork consists exclusively of single M/L segments.
        if (!/^\s*M\s*[-+.\d\s,eE]+L\s*[-+.\d\s,eE]+\s*$/i.test(d)) continue;
        const values = d.match(/[-+]?(?:\d*\.)?\d+(?:e[-+]?\d+)?/gi)?.map(Number);
        if (!values || values.length !== 4 || values.some(v => !Number.isFinite(v))) continue;
        const a = vertex(values[0], values[1]), b = vertex(values[2], values[3]);
        const length = Math.hypot(b.x - a.x, b.y - a.y);
        const key = [a.key, b.key].sort().join('|');
        if (length < 0.01 || seen.has(key)) continue;
        seen.add(key);
        const rawOpacity = Number.parseFloat(path.getAttribute('stroke-opacity') || '1');
        const opacity = Number.isFinite(rawOpacity) ? clamp(rawOpacity) : 1;
        const edge = {id: groupId + ':' + edges.length, a, b, length, opacity, visible: visibleInterval(a, b)};
        edges.push(edge);
        a.edges.push(edge);
        b.edges.push(edge);
      }
      const maxOpacity = Math.max(0.001, ...edges.map(e => e.opacity));
      const seeds = edges.filter(e => e.visible && (e.visible[1] - e.visible[0]) * e.length > 14 && e.opacity > maxOpacity * 0.23);
      return {id: groupId, group, edges, vertices, maxOpacity, seeds: seeds.length ? seeds : edges};
    }

    const graphs = {upper: makeGraph('upper-bank'), lower: makeGraph('lower-bank')};
    if (!graphs.upper?.edges.length || !graphs.lower?.edges.length) return;

    const overlay = document.createElementNS(NS, 'g');
    overlay.setAttribute('data-pulses', '');
    overlay.setAttribute('fill', 'none');
    overlay.setAttribute('stroke', '#0AA5DE');
    overlay.setAttribute('stroke-width', '1.7');
    overlay.setAttribute('stroke-linecap', 'butt');
    overlay.setAttribute('stroke-linejoin', 'miter');
    overlay.setAttribute('pointer-events', 'none');
    overlay.setAttribute('aria-hidden', 'true');
    svg.appendChild(overlay);

    // Keep each bank and its blue overlay in the same transformed coordinate system.
    // Uniform CSS-pixel scale avoids stretched triangles in a tall mobile hero.
    for (const graph of Object.values(graphs)) {
      graph.layer = document.createElementNS(NS, 'g');
      graph.layer.setAttribute('data-pulse-bank', graph.id);
      overlay.appendChild(graph.layer);
    }

    function positionBanks() {
      const rect = root.getBoundingClientRect();
      const width = rect.width, height = rect.height;
      if (!(width > 0 && height > 0)) return;
      const sx = width / viewBox.width, sy = height / viewBox.height;
      const scale = Math.min(width / (width <= 900 ? 1100 : 1920), height / 900);
      for (const [bank, graph] of Object.entries(graphs)) {
        const tx = bank === 'upper' ? width - 1920 * scale : 0;
        const ty = bank === 'lower' ? height - 900 * scale : 0;
        const transform = `matrix(${scale / sx} 0 0 ${scale / sy} ${tx / sx} ${ty / sy})`;
        graph.group.setAttribute('transform', transform);
        graph.layer.setAttribute('transform', transform);
        const viewport = {left: -tx / scale, right: (width - tx) / scale,
          top: -ty / scale, bottom: (height - ty) / scale};
        for (const edge of graph.edges) edge.visible = visibleInterval(edge.a, edge.b, viewport);
        graph.seeds = graph.edges.filter(e => e.visible &&
          (e.visible[1] - e.visible[0]) * e.length > 14 && e.opacity > graph.maxOpacity * 0.23);
        // The supplied banks always intersect the frame; guard a future empty crop explicitly.
        if (!graph.seeds.length) graph.seeds = graph.edges.filter(e => e.visible);
      }
    }

    let pulses = [];
    let nextId = 0;
    let playing = root.dataset.motionChoice === 'play' ||
      (root.dataset.motionChoice !== 'pause' && !reducedMotion.matches);
    let intersecting = false;
    let destroyed = false;
    let raf = 0;
    let previousTime = null;
    let renderedCount = 0;

    function pickWeighted(items, weight) {
      const weights = items.map(weight);
      let choice = Math.random() * weights.reduce((sum, value) => sum + value, 0);
      for (let i = 0; i < items.length; i++) {
        choice -= weights[i];
        if (choice <= 0) return items[i];
      }
      return items[items.length - 1];
    }

    function directed(edge, from) {
      return {edge, from, to: edge.a === from ? edge.b : edge.a, length: edge.length};
    }

    function seed(pulse) {
      const graph = pulse.graph;
      if (!graph.seeds.length) return;
      const edge = pickWeighted(graph.seeds, e => {
        const visibleFraction = e.visible ? e.visible[1] - e.visible[0] : 0.1;
        return Math.max(0.001, e.length * visibleFraction * e.opacity);
      });
      const from = Math.random() < 0.5 ? edge.a : edge.b;
      const interval = edge.visible || [0.15, 0.85];
      const t = random(interval[0], interval[1]);
      pulse.current = directed(edge, from);
      pulse.offset = (from === edge.a ? t : 1 - t) * edge.length;
      pulse.history = [];
      pulse.speed = random(280, 840);
      pulse.currentSpeed = pulse.speed;
      pulse.tailLength = random(57, 74);
      pulse.life = random(6, 10);
      pulse.age = 0;
      pulse.wait = 0;
    }

    function newPulse(bank, delay) {
      const group = document.createElementNS(NS, 'g');
      const pulse = {id: ++nextId, bank, graph: graphs[bank], group, fragments: []};
      group.setAttribute('data-pulse-id', String(pulse.id));
      group.setAttribute('data-bank', bank);
      pulse.graph.layer.appendChild(group);
      seed(pulse);
      pulse.wait = delay;
      return pulse;
    }

    function reconcileCount() {
      const narrow = (root.getBoundingClientRect().width || window.innerWidth) <= 520;
      const desired = narrow ? {upper: 2, lower: 2} : {upper: 4, lower: 2};
      for (const bank of ['upper', 'lower']) {
        let matches = pulses.filter(p => p.bank === bank);
        while (matches.length > desired[bank]) {
          const removed = matches.pop();
          removed.group.remove();
          pulses = pulses.filter(p => p !== removed);
        }
        while (matches.length < desired[bank]) {
          const pulse = newPulse(bank, pulses.length * 0.25);
          pulses.push(pulse);
          matches.push(pulse);
        }
      }
    }

    function nextSegment(pulse) {
      const current = pulse.current, at = current.to;
      let candidates = at.edges.filter(e => e !== current.edge);
      if (!candidates.length) candidates = [current.edge];
      const ix = (at.x - current.from.x) / current.length;
      const iy = (at.y - current.from.y) / current.length;
      const chosen = pickWeighted(candidates, edge => {
        const to = edge.a === at ? edge.b : edge.a;
        const dot = clamp(ix * (to.x - at.x) / edge.length + iy * (to.y - at.y) / edge.length, -1, 1);
        const continuation = 0.6 + 0.9 * (dot + 1) / 2;
        const visible = edge.visible ? edge.visible[1] - edge.visible[0] : 0;
        const localFade = edge.opacity / pulse.graph.maxOpacity;
        return continuation * (0.35 + 0.65 * visible) * (0.35 + 0.65 * localFade);
      });
      pulse.history.push(current);
      pulse.current = directed(chosen, at);
      // Only a few recent edges are needed to draw a 74-unit tail.
      let retained = 0;
      for (let i = pulse.history.length - 1; i >= 0; i--) {
        retained += pulse.history[i].length;
        if (retained > pulse.tailLength + 10) {
          pulse.history.splice(0, i);
          break;
        }
      }
    }

    function advance(pulse, dt) {
      if (pulse.wait > 0) {
        pulse.wait -= dt;
        if (pulse.wait > 0) return;
        seed(pulse);
      }
      pulse.age += dt;
      if (pulse.age >= pulse.life) {
        pulse.wait = random(0.25, 0.9);
        return;
      }
      // Each spark keeps its independently chosen fast speed throughout the run.
      pulse.offset += pulse.speed * dt;
      let guard = 0;
      while (pulse.offset >= pulse.current.length && guard++ < 100) {
        pulse.offset -= pulse.current.length;
        nextSegment(pulse);
      }
    }

    function taper(u) {
      if (u <= 0 || u >= 1) return 0;
      return u < 0.76
        ? Math.pow(Math.sin((u / 0.76) * Math.PI / 2), 1.3)
        : Math.pow(Math.cos(((u - 0.76) / 0.24) * Math.PI / 2), 1.3);
    }

    function renderPulse(pulse) {
      const lifeFade = Math.min(ease(pulse.age / 0.35), ease((pulse.life - pulse.age) / 0.8));
      if (pulse.wait > 0 || lifeFade <= 0.001) {
        pulse.group.setAttribute('display', 'none');
        return false;
      }
      pulse.group.removeAttribute('display');
      let remaining = pulse.tailLength;
      let behind = 0;
      let used = 0;
      const segments = [...pulse.history, pulse.current];
      for (let i = segments.length - 1; i >= 0 && remaining > 0; i--) {
        const segment = segments[i];
        const end = i === segments.length - 1 ? pulse.offset : segment.length;
        const take = Math.min(end, remaining);
        const start = end - take;
        // Every fragment stays on one existing edge; bends never form shortcuts.
        const subdivisions = Math.max(1, Math.ceil(take / 4));
        for (let j = 0; j < subdivisions; j++) {
          const near = end - take * j / subdivisions;
          const far = end - take * (j + 1) / subdivisions;
          const middleBehind = behind + end - (near + far) / 2;
          const envelope = taper(1 - middleBehind / pulse.tailLength);
          const localFade = segment.edge.opacity / pulse.graph.maxOpacity;
          const opacity = 0.65 * lifeFade * envelope * localFade;
          if (opacity < 0.002 || near - far < 0.001) continue;
          let fragment = pulse.fragments[used];
          if (!fragment) {
            fragment = document.createElementNS(NS, 'path');
            pulse.group.appendChild(fragment);
            pulse.fragments.push(fragment);
          }
          const a = interpolate(segment.from, segment.to, far / segment.length);
          const b = interpolate(segment.from, segment.to, near / segment.length);
          fragment.setAttribute('d', `M${a.x.toFixed(3)} ${a.y.toFixed(3)}L${b.x.toFixed(3)} ${b.y.toFixed(3)}`);
          fragment.setAttribute('stroke-opacity', opacity.toFixed(4));
          fragment.removeAttribute('display');
          used++;
        }
        remaining -= take;
        behind += take;
        if (start > 0) break;
      }
      for (let i = used; i < pulse.fragments.length; i++) pulse.fragments[i].setAttribute('display', 'none');
      return used > 0;
    }

    function active() { return playing && intersecting && !document.hidden && !destroyed && root.isConnected; }

    function publishState() {
      const runningValue = String(active());
      const countValue = String(renderedCount);
      if (root.dataset.running !== runningValue) root.dataset.running = runningValue;
      if (root.dataset.pulseCount !== countValue) root.dataset.pulseCount = countValue;
      if (toggle) {
        const label = playing ? 'Pause background animation' : 'Play background animation';
        toggle.title = label;
        if (toggle.getAttribute('aria-pressed') !== String(playing)) {
          toggle.setAttribute('aria-pressed', String(playing));
          toggle.setAttribute('aria-label', label);
        }
      }
    }

    function tick(time) {
      raf = 0;
      if (!root.isConnected) { destroy(); return; }
      // A restored page may expose a new preference before dispatching its change event.
      // Check it before advancing any decorative motion as well as in the listener.
      if (playing && reducedMotion.matches && root.dataset.motionChoice !== 'play') {
        onReducedMotion(reducedMotion);
      }
      if (!active()) { previousTime = null; publishState(); return; }
      const dt = previousTime === null ? 0 : Math.min(0.08, Math.max(0, (time - previousTime) / 1000));
      previousTime = time;
      renderedCount = 0;
      for (const pulse of pulses) {
        advance(pulse, dt);
        if (renderPulse(pulse)) renderedCount++;
      }
      publishState();
      raf = requestAnimationFrame(tick);
    }

    function sync() {
      if (raf) cancelAnimationFrame(raf);
      raf = 0;
      previousTime = null;
      publishState();
      if (active()) raf = requestAnimationFrame(tick);
    }

    function onToggle() {
      playing = !playing;
      root.dataset.motionChoice = playing ? 'play' : 'pause';
      sync();
    }
    function onVisibility() { sync(); }
    function onReducedMotion(event) {
      if (event.matches) {
        playing = false;
        for (const pulse of pulses) pulse.group.setAttribute('display', 'none');
        renderedCount = 0;
        sync();
      } else {
        playing = root.dataset.motionChoice !== 'pause';
        sync();
      }
    }
    function onResize() {
      if (destroyed) return;
      positionBanks();
      reconcileCount();
      if (!playing) {
        for (const pulse of pulses) if (!pulse.fragments.length) pulse.group.setAttribute('display', 'none');
      }
      publishState();
    }

    const intersectionObserver = typeof IntersectionObserver === 'function' ? new IntersectionObserver(entries => {
      const entry = entries.find(item => item.target === root);
      if (!entry) return;
      intersecting = entry.isIntersecting && entry.intersectionRect.width > 0 && entry.intersectionRect.height > 0;
      sync();
    }) : null;
    const resizeObserver = typeof ResizeObserver === 'function' ? new ResizeObserver(onResize) : null;
    const removalObserver = new MutationObserver(() => { if (!root.isConnected) destroy(); });
    function destroy() {
      if (destroyed) return;
      destroyed = true;
      if (raf) cancelAnimationFrame(raf);
      raf = 0;
      resizeObserver?.disconnect();
      removalObserver.disconnect();
      intersectionObserver?.disconnect();
      toggle?.removeEventListener('click', onToggle);
      document.removeEventListener('visibilitychange', onVisibility);
      window.removeEventListener('resize', onResize);
      if (reducedMotion.removeEventListener) reducedMotion.removeEventListener('change', onReducedMotion);
      else reducedMotion.removeListener(onReducedMotion);
      root.dataset.running = 'false';
      root.dataset.pulseCount = '0';
      overlay.remove();
      if (toggle) toggle.hidden = true;
      delete root.__pulseController;
    }

    Object.defineProperty(root, '__pulseController', {
      configurable: true,
      value: Object.freeze({
        destroy,
        snapshot: () => ({
          running: active(), requestedPlaying: playing, reducedMotion: reducedMotion.matches,
          inViewport: intersecting, framePending: Boolean(raf),
          pulseCount: renderedCount,
          graphEdges: {upper: graphs.upper.edges.length, lower: graphs.lower.edges.length},
          pulses: pulses.map(p => ({
            id: p.id, bank: p.bank, waiting: p.wait > 0, age: p.age,
            speed: p.speed, currentSpeed: p.currentSpeed || p.speed, tailLength: p.tailLength, life: p.life, wait: p.wait,
            position: interpolate(p.current.from, p.current.to, p.offset / p.current.length),
            edge: {id: p.current.edge.id, from: {x: p.current.from.x, y: p.current.from.y}, to: {x: p.current.to.x, y: p.current.to.y}},
            offset: p.offset,
            route: [...p.history, p.current].map(s => ({id: s.edge.id, from: {x: s.from.x, y: s.from.y}, to: {x: s.to.x, y: s.to.y}}))
          }))
        })
      })
    });

    positionBanks();
    reconcileCount();
    if (toggle) toggle.hidden = false;
    toggle?.addEventListener('click', onToggle);
    document.addEventListener('visibilitychange', onVisibility);
    if (reducedMotion.addEventListener) reducedMotion.addEventListener('change', onReducedMotion);
    else reducedMotion.addListener(onReducedMotion);
    if (resizeObserver) resizeObserver.observe(root);
    else window.addEventListener('resize', onResize);
    removalObserver.observe(document.documentElement, {childList: true, subtree: true});
    if (intersectionObserver) intersectionObserver.observe(root);
    else {
      const rect = root.getBoundingClientRect();
      intersecting = rect.bottom > 0 && rect.top < window.innerHeight;
    }
    sync();
  }

  // Zensical currently uses full document navigation. pagehide releases the component;
  // pageshow also handles restoration from Safari's back/forward cache. The optional
  // document$ hook keeps the same ownership if native instant navigation is enabled later.
  let subscription = null;
  function mount() {
    createNetwork(document.getElementById('network-pulse-preview'));
  }
  function connect() {
    if (!subscription && typeof document$ !== 'undefined') subscription = document$.subscribe(mount);
    mount();
  }
  function leave() {
    document.getElementById('network-pulse-preview')?.__pulseController?.destroy();
    subscription?.unsubscribe();
    subscription = null;
  }
  window.__ediNetworkMount = connect;
  window.addEventListener('pagehide', leave);
  window.addEventListener('pageshow', connect);
  connect();
})();
