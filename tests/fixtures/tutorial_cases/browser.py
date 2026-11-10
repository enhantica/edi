"""Observe delivered views in offline Chromium, including the real Plotly request boundary."""

import json
import subprocess

from bs4 import BeautifulSoup

from tests.system.py.test_tutorial_pattern_toolbar import chromium

CAPTURE = """<script>
window.__drawingRequests = [];
if (window.Plotly) {
  const original = window.Plotly.newPlot;
  window.Plotly.newPlot = function(figure, traces, layout, config) {
    window.__drawingRequests.push(JSON.parse(JSON.stringify({traces, layout, config})));
    return original.apply(this, arguments);
  };
}
</script>"""
PROBE = """<script>
window.addEventListener('load', () => setTimeout(() => {
  try {
  const rect = element => {
    const box = element.getBoundingClientRect();
    return {left: box.left, right: box.right, top: box.top, bottom: box.bottom};
  };
  const controls = figure => [...figure.querySelectorAll('button, select')].map(button => ({
    tag: button.tagName, title: button.title || button.getAttribute('aria-label'),
    html: button.innerHTML, text: button.textContent, rect: rect(button),
    options: button.tagName === 'SELECT' ? [...button.options].map(o => o.text) : null,
    group: button.parentElement.className,
    previous: button.previousElementSibling && {
      tag: button.previousElementSibling.tagName,
      class: button.previousElementSibling.className,
      width: button.previousElementSibling.getBoundingClientRect().width,
    },
  }));
  const tables = [...document.querySelectorAll('table')]
    .filter(t => t.querySelectorAll('th').length >= 4)
    .map(table => ({
      headers: [...table.querySelectorAll('thead th')].map(c => c.textContent.trim()),
      cells: [...table.querySelectorAll('th, td')].slice(0, 40).map(cell => {
        const style = getComputedStyle(cell);
        return {padding: [style.paddingTop, style.paddingRight,
                          style.paddingBottom, style.paddingLeft]};
      }),
      stripes: [...table.querySelectorAll('tbody tr')].slice(0, 4).map(row => ({
        row: getComputedStyle(row).backgroundColor,
        cell: row.cells.length ? getComputedStyle(row.cells[0]).backgroundColor : null,
      })),
    }));
  const figures = [...document.querySelectorAll('.figure')].map(figure => ({
    kind: figure.className, controls: controls(figure),
    snapshots: [...figure.querySelectorAll('.viewer-snapshot')].map(rect),
    canvas: !!figure.querySelector('canvas'),
  }));
  const plot = document.querySelector(
    '.pattern-figure.js-plotly-plot, .pattern-figure .js-plotly-plot');
  const prose = document.querySelector('.md-typeset') || document.body;
  const paragraph = [...prose.querySelectorAll('p')].find(p =>
    !p.querySelector('a, svg, span') && p.textContent.trim()) || prose;
  const typography = element => {
    const style = element.ownerDocument.defaultView.getComputedStyle(element);
    return {family: style.fontFamily, weight: style.fontWeight, size: style.fontSize,
      colour: element.namespaceURI === 'http://www.w3.org/2000/svg' ? style.fill : style.color};
  };
  const siteLink = prose.querySelector('a[href]');
  const docs = {font: getComputedStyle(prose).fontFamily,
    paragraph: typography(paragraph),
    link: siteLink && getComputedStyle(siteLink).color, frames: [], chartText: []};
  const readTables = doc => [...doc.querySelectorAll('table')].map(table => ({
    bodyText: [...table.querySelectorAll('tbody td')].flatMap(cell => {
      const walker = doc.createTreeWalker(cell, NodeFilter.SHOW_TEXT), result = [];
      while (walker.nextNode()) {
        const parent = walker.currentNode.parentElement;
        if (walker.currentNode.textContent.trim() && !parent.closest('a'))
          result.push(typography(parent));
      }
      return result;
    }),
    fonts: [...table.querySelectorAll('th, td')].flatMap(cell => {
      const walker = doc.createTreeWalker(cell, NodeFilter.SHOW_TEXT), fonts = [];
      while (walker.nextNode()) {
        if (walker.currentNode.textContent.trim())
          fonts.push(doc.defaultView.getComputedStyle(walker.currentNode.parentElement).fontFamily);
      }
      return fonts;
    }),
    links: [...table.querySelectorAll('a[href]')].map(link => ({
      colour: doc.defaultView.getComputedStyle(link).color,
      visited: [...doc.styleSheets].flatMap(sheet => {
        let rules; try {rules = [...sheet.cssRules];} catch (_) {return [];}
        return rules.filter(rule => rule.selectorText && rule.selectorText.includes(':visited')
          && rule.style.color).filter(rule => {
            try {return link.matches(rule.selectorText.replaceAll(':visited', ':any-link'));}
            catch (_) {return false;}
          }).map(rule => {
            const clone = link.cloneNode(true);
            clone.style.color = rule.style.color; link.parentElement.appendChild(clone);
            const colour = doc.defaultView.getComputedStyle(clone).color; clone.remove();
            return colour;
          });
      }),
    })),
  }));
  docs.tables = readTables(document);
  const chartText = doc => [...doc.querySelectorAll(
    '.xtick text, .ytick text, .y2tick text, .y3tick text, .xtitle, .ytitle, .y3title')]
    .filter(element => element.textContent.trim()).map(typography);
  docs.chartText.push(...chartText(document));
  for (const frame of document.querySelectorAll('iframe')) {
    if (frame.contentDocument) {
      docs.frames.push(...readTables(frame.contentDocument));
      docs.chartText.push(...chartText(frame.contentDocument));
    }
  }
  const result = {figures, tables, docs, requests: window.__drawingRequests,
    hovers: {}, traces: [], structureLabels: [], tabs: [], filters: [],
    modebar: plot && plot._context && plot._context.displayModeBar};
  result.filters = [...document.querySelectorAll('.ed-example-filters')].map(group => ({
    selectors: [...group.querySelectorAll('select[data-example-filter]')].map(select => ({
      facet: select.dataset.exampleFilter, rect: rect(select),
    })),
    search: group.querySelector('[data-example-search]')
      && rect(group.querySelector('[data-example-search]')),
    reset: group.querySelector('[data-example-reset]')
      && rect(group.querySelector('[data-example-reset]')),
  }));
  const tabSets = [...document.querySelectorAll('.tabbed-set')].filter(set => {
    const labels = set.querySelector('.tabbed-labels');
    return labels && labels.textContent.includes('Standalone executable')
      && labels.textContent.includes('Python package');
  });
  if (tabSets.length >= 2) {
    tabSets[0].querySelector('.tabbed-labels').querySelectorAll('label')[1].click();
    result.tabs = tabSets.map(set => [...set.querySelectorAll(':scope > input')]
      .map(input => input.checked));
  }
  if (plot && window.__hoverReference) {
    const reference = window.__hoverReference;
    const toggle = [...document.querySelectorAll('button')]
      .find(button => button.title === reference.hover_button);
    result.traces = plot.data.map(trace => ({name: trace.name, yaxis: trace.yaxis,
      marker: trace.marker, line: trace.line, meta: trace.meta, text: trace.text}));
    result.structureLabels = [...plot.querySelectorAll('*')].filter(element =>
      element.textContent.trim() === 'lbco' && element.querySelector('svg path'))
      .map(element => ({html: element.innerHTML, colour: getComputedStyle(element).color}));
    for (const key of ['point', 'tick']) {
      const target = reference[key];
      let found = null;
      plot.data.forEach((trace, curveNumber) => {
        if (!trace.x || !trace.y || (key === 'tick') !== (trace.yaxis === 'y2')) return;
        for (let i = 0; i < trace.x.length; ++i) {
          if (trace.x[i] == null || trace.y[i] == null) continue;
          const distance = Math.abs(trace.x[i] - target.x)
            + Math.abs(trace.y[i] - target.y) * 1e-10;
          if (!found || distance < found.distance) found = {curveNumber, i, distance};
        }
      });
      if (!found) {result.hovers[key] = {missing: true}; continue;}
      const trace = plot.data[found.curveNumber];
      window.Plotly.Fx.hover(plot, [{curveNumber: found.curveNumber, pointNumber: found.i}],
        key === 'tick' ? 'xy2' : 'xy');
      // The real Plotly event shape, populated from the trace actually drawn above.
      const xaxis = plot._fullLayout.xaxis;
      const yaxis = key === 'tick' ? plot._fullLayout.yaxis2 : plot._fullLayout.yaxis;
      const box = plot.getBoundingClientRect();
      const clientX = box.left + xaxis._offset + xaxis.l2p(trace.x[found.i]);
      const clientY = box.top + yaxis._offset + yaxis.l2p(trace.y[found.i]);
      const readout = () => {
        plot.emit('plotly_hover', {points: [{data: trace,
          fullData: plot._fullData[found.curveNumber],
          curveNumber: found.curveNumber, pointIndex: found.i, pointNumber: found.i,
          x: trace.x[found.i], y: trace.y[found.i],
          text: Array.isArray(trace.text) ? trace.text[found.i] : trace.text,
          customdata: trace.customdata && trace.customdata[found.i],
          xaxis: plot._fullLayout.xaxis,
          yaxis: key === 'tick' ? plot._fullLayout.yaxis2 : plot._fullLayout.yaxis}],
          event: new MouseEvent('mousemove', {clientX, clientY})});
        return [...document.querySelectorAll(
          '[role=tooltip], [class*=hover], [class*=readout]')].filter(element => {
            const box = element.getBoundingClientRect(), style = getComputedStyle(element);
            return box.width && box.height && style.visibility !== 'hidden'
              && style.display !== 'none';
          });
      };
      let boxes = readout();
      if (toggle && !boxes.some(box => target.lines.every(line =>
          box.textContent.includes(line.text)))) {
        toggle.click();
        boxes = readout();
      }
      result.hovers[key] = {distance: found.distance, boxes: boxes.map(box => ({
        html: box.innerHTML, text: box.textContent,
        spans: [...box.querySelectorAll('span, tspan')].map(span => ({
          text: span.textContent, colour: getComputedStyle(span).color,
          fill: getComputedStyle(span).fill,
        })),
      }))};
      window.Plotly.Fx.unhover(plot);
      plot.emit('plotly_unhover', {});
    }
  }
  const receipt = document.createElement('pre'); receipt.id = 'view-witness';
  receipt.textContent = JSON.stringify(result); document.body.appendChild(receipt);
  } catch (error) {
    const receipt = document.createElement('pre'); receipt.id = 'view-witness';
    receipt.textContent = JSON.stringify({observer_error: String(error.stack)});
    document.body.appendChild(receipt);
  }
}, 1000));
</script>"""


def observe_html(source, folder, *, reference=None):
    folder.mkdir()
    reference_script = (
        '<script>window.__hoverReference = ' + json.dumps(reference) + ';</script>'
        if reference is not None
        else ''
    )
    source = source.replace('<script type="module"', CAPTURE + '<script type="module"', 1)
    path = folder / 'view.html'
    path.write_text(source.replace('</body>', reference_script + PROBE + '</body>'))
    run = subprocess.run(
        [
            chromium(),
            '--headless',
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--enable-unsafe-swiftshader',
            '--use-angle=swiftshader',
            '--enable-webgl',
            '--no-first-run',
            '--disable-background-networking',
            '--disable-extensions',
            '--proxy-server=direct://',
            '--proxy-bypass-list=*',
            '--host-resolver-rules=MAP * ~NOTFOUND',
            '--allow-file-access-from-files',
            '--user-data-dir=' + str(folder / 'profile'),
            '--virtual-time-budget=3000',
            '--dump-dom',
            path.as_uri(),
        ],
        capture_output=True,
        text=True,
        check=False,
        timeout=25,
    )
    (folder / 'browser.stderr').write_text(run.stderr)
    assert run.returncode == 0, 'Gate 9: the real offline browser must finish the delivered view'
    witness = BeautifulSoup(run.stdout, 'html.parser').find(id='view-witness')
    assert witness is not None, 'Gate 9: the delivered view executes the passive browser observer'
    result = json.loads(witness.get_text())
    assert 'observer_error' not in result, 'Gate 9: browser observer error: ' + str(result)
    (folder / 'witness.json').write_text(json.dumps(result, indent=2))
    return result
