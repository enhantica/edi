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
      const padding = (region.hasAttribute('data-gui-inset') ? -Number(region.dataset.guiInset) : 1.5) / scale;
      const parts = JSON.parse(region.dataset.guiParts);
      const [x, y, width, height] = parts[0];
      const left = x - padding, top = y - padding;
      const right = x + width + padding, bottom = y + height + padding;
      const points = [[left, top]];
      if (parts.length === 2) {
        const [tx, ty, tw] = parts[1];
        points.push([tx - padding, top], [tx - padding, ty - padding],
          [tx + tw + padding, ty - padding], [tx + tw + padding, top]);
      }
      points.push([right, top], [right, bottom], [left, bottom]);
      region.setAttribute('d', 'M' + points.map(point => point.join(' ')).join(' L') + ' Z');
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
  if (typeof document$ !== 'undefined') document$.subscribe(initialize);
  else initialize();
})();
