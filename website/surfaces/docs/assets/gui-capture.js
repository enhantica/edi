(() => {
  if (window.ediGuiCaptureInstalled) return;
  window.ediGuiCaptureInstalled = true;
  let dialog, opener;
  const geometry = svg => {
    const scale = svg.getBoundingClientRect().width / svg.viewBox.baseVal.width;
    if (!scale) return;
    const percent = parseFloat(getComputedStyle(svg).getPropertyValue('--ed-screenshot-radius'));
    const radius = svg.viewBox.baseVal.width * percent / 100;
    svg.querySelectorAll('clipPath rect, .gui-image-frame').forEach(frame => frame.setAttribute('rx', radius));
    svg.querySelectorAll('[data-gui-region], [data-gui-navigation]').forEach(region => {
      // The outline sits inside its area, so neighbouring areas never overlap.
      const inset = 1 / scale, radius = 4 / scale;
      const parts = JSON.parse(region.dataset.guiParts);
      const [x, y, width, height] = parts[0];
      const left = x + inset, top = y + inset;
      const right = x + width - inset, bottom = y + height - inset;
      const points = [[left, top]];
      if (parts.length === 2) {
        const [tx, ty, tw] = parts[1];
        points.push([tx + inset, top], [tx + inset, ty + inset],
          [tx + tw - inset, ty + inset], [tx + tw - inset, top]);
      }
      points.push([right, top], [right, bottom], [left, bottom]);
      // A tab flush with its panel's edge repeats a corner; a repeated point has no direction.
      const corners = points.filter((point, number) => {
        const before = points.at(number - 1);
        return point[0] !== before[0] || point[1] !== before[1];
      });
      const path = corners.map((point, number) => {
        const [before, after] = [corners.at(number - 1), corners[(number + 1) % corners.length]];
        const [start, end] = [before, after].map(other => {
          const length = Math.hypot(other[0] - point[0], other[1] - point[1]);
          const share = Math.min(radius, length / 2) / length;
          return [point[0] + (other[0] - point[0]) * share, point[1] + (other[1] - point[1]) * share];
        });
        return `${number ? 'L' : 'M'}${start.join(' ')} Q${point.join(' ')} ${end.join(' ')}`;
      });
      region.setAttribute('d', path.join(' ') + ' Z');
    });
  };
  const descriptionHeight = viewer => {
    const width = viewer.getBoundingClientRect().width;
    if (!width) return;
    let height = 0;
    viewer.querySelectorAll('.gui-view-description').forEach(description => {
      const measure = description.cloneNode(true);
      measure.setAttribute('aria-hidden', 'true');
      measure.style.cssText = `position:absolute;visibility:hidden;pointer-events:none;min-block-size:0;block-size:auto;inline-size:${width}px`;
      viewer.append(measure);
      height = Math.max(height, measure.getBoundingClientRect().height);
      measure.remove();
    });
    const value = `${Math.ceil(height)}px`;
    if (viewer.style.getPropertyValue('--gui-description-height') !== value) {
      viewer.style.setProperty('--gui-description-height', value);
    }
  };
  const observer = new ResizeObserver(entries => entries.forEach(entry => {
    if (entry.target.matches('.gui-viewer')) descriptionHeight(entry.target);
    else geometry(entry.target);
  }));
  const close = () => dialog?.close();
  const show = link => {
    if (!dialog) {
      dialog = document.createElement('dialog');
      dialog.className = 'gui-lightbox';
      dialog.setAttribute('aria-labelledby', 'gui-lightbox-title');
      dialog.innerHTML = '<header class="gui-lightbox-header"><h2 id="gui-lightbox-title"></h2>' +
        '<button class="gui-lightbox-close" type="button" aria-label="Close enlarged screenshot" autofocus>' +
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg></button></header>' +
        '<div class="gui-lightbox-stage"></div>';
      document.body.append(dialog);
      dialog.querySelector('button').addEventListener('click', close);
      dialog.addEventListener('keydown', event => {
        if (event.key === 'Tab') {
          event.preventDefault();
          dialog.querySelector('button').focus();
        }
      });
      dialog.addEventListener('click', event => {
        if (event.target === dialog || event.target.classList.contains('gui-lightbox-stage')) close();
      });
      dialog.addEventListener('close', () => {
        document.documentElement.classList.remove('gui-lightbox-open');
        const svg = dialog.querySelector('.gui-capture');
        if (svg) observer.unobserve(svg);
        dialog.querySelector('.gui-lightbox-stage').replaceChildren();
        if (opener?.isConnected) opener.focus({preventScroll: true});
      });
    }
    opener = link;
    const svg = link.querySelector('.gui-capture').cloneNode(true);
    const clip = svg.querySelector('clipPath');
    const id = clip.id + '-lightbox';
    clip.id = id;
    svg.querySelector('image').setAttribute('clip-path', `url(#${id})`);
    dialog.querySelector('h2').textContent = svg.querySelector('title').textContent;
    dialog.querySelector('.gui-lightbox-stage').replaceChildren(svg);
    dialog.showModal();
    document.documentElement.classList.add('gui-lightbox-open');
    observer.observe(svg);
    geometry(svg);
  };
  document.addEventListener('click', event => {
    const link = event.target.closest('[data-gui-open]');
    if (link) {
      if (event.button || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      show(link);
      return;
    }
  });
  const initialize = () => {
    close();
    observer.disconnect();
    document.querySelectorAll('svg.gui-capture').forEach(svg => {
      observer.observe(svg);
      geometry(svg);
    });
    document.querySelectorAll('.gui-viewer').forEach(viewer => {
      observer.observe(viewer);
      descriptionHeight(viewer);
    });
  };
  // Dark screenshots sit in dark/ beside the light ones and share their highlights.
  const syncTheme = () => {
    const dark = document.body.dataset.mdColorScheme === 'slate';
    document.querySelectorAll('[data-gui-dark]').forEach(element => {
      element.dataset.guiLight ||= element.getAttribute('href');
      const light = element.dataset.guiLight;
      element.setAttribute('href', dark
        ? light.replace(/\/([^/?]+)\?v=.*$/, `/dark/$1?v=${element.dataset.guiDark}`)
        : light);
    });
  };
  new MutationObserver(syncTheme).observe(document.body, {attributes: true, attributeFilter: ['data-md-color-scheme']});
  syncTheme();
  if (typeof document$ !== 'undefined') document$.subscribe(initialize);
  else initialize();
})();
