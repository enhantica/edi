// SPDX-License-Identifier: BSD-3-Clause
/* Filter the generated tutorial table; unenhanced HTML keeps every row. */
(() => {
  function setup() {
    document.querySelectorAll('[data-example-catalogue]').forEach(catalogue => {
      if (catalogue.dataset.ready) return;
      catalogue.dataset.ready = 'true';
      const rows = [...catalogue.querySelectorAll('[data-example-row]')];
      const sections = [...catalogue.querySelectorAll('[data-tutorial-section]')];
      const search = catalogue.querySelector('[data-example-search]');
      const reset = catalogue.querySelector('[data-example-reset]');
      const selectors = [...catalogue.querySelectorAll('[data-example-filter]')];
      function update() {
        const words = search.value.toLocaleLowerCase().trim().split(/\s+/).filter(Boolean);
        let count = 0;
        for (const row of rows) {
          const matches = words.every(word => row.dataset.search.includes(word)) && selectors.every(select => {
            const tokens = row.getAttribute('data-' + select.dataset.exampleFilter.toLowerCase());
            return !select.value || (tokens !== null && JSON.parse(tokens).includes(select.value));
          });
          row.hidden = !matches;
          count += Number(matches);
        }
        // A section header shows while any of its rows does.
        for (const header of sections) {
          let next = header.nextElementSibling;
          let shown = false;
          while (next && !next.hasAttribute('data-tutorial-section')) {
            shown ||= !next.hidden;
            next = next.nextElementSibling;
          }
          header.hidden = !shown;
        }
        // The table's closing line follows its last visible row, not the last row of the page.
        const visible = rows.filter(row => !row.hidden);
        for (const row of rows) row.classList.toggle('ed-last-visible', row === visible[visible.length - 1]);
        catalogue.querySelector('[data-example-count]').textContent = `${count} of ${rows.length} tutorials`;
      }
      if (reset) {
        reset.addEventListener('click', () => {
          search.value = '';
          for (const select of selectors) select.value = '';
          update();
          search.focus();
        });
      }
      catalogue.addEventListener('input', update);
      catalogue.addEventListener('change', update);
      update();
    });
  }
  // The Features page: the same filter bar over its tables' rows (owner record 2026-11-09). A row matches when it holds
  // every searched word and, for each chosen type, it names that value or names nothing of that kind; an "All types"
  // row matches every type. A table
  // with no matching row is hidden with its heading, a section with no table left with its heading, and the choice
  // is kept in the URL.
  function setupFeatures() {
    const bar = document.querySelector('[data-feature-bar]');
    if (!bar || bar.dataset.ready) return;
    bar.dataset.ready = 'true';
    const content = bar.closest('.md-content') || document;
    const selectors = [...bar.querySelectorAll('[data-feature-filter]')];
    const search = bar.querySelector('[data-feature-search]');
    const tables = [...content.querySelectorAll('table')].filter(table => table.querySelector('td .ed-tag'));
    const holder = table => table.closest('.md-typeset__scrollwrap') || table;
    const heading = table => {
      let node = holder(table).previousElementSibling;
      while (node && !/^H[23]$/.test(node.tagName)) node = node.previousElementSibling;
      return node;
    };
    function matches(row) {
      const words = search.value.toLocaleLowerCase().trim().split(/\s+/).filter(Boolean);
      const text = row.textContent.toLocaleLowerCase();
      if (!words.every(word => text.includes(word))) return false;
      const chips = [...row.cells[0].querySelectorAll('.ed-tag')];
      if (chips.some(chip => chip.dataset.edTag === 'all')) return true;
      return selectors.every(select => {
        if (!select.value) return true;
        const named = chips.filter(chip => chip.dataset.edTag === select.dataset.featureFilter);
        return named.length === 0 || named.some(chip => chip.dataset.edToken === select.value);
      });
    }
    function update() {
      for (const table of tables) {
        let shown = false;
        for (const row of table.tBodies[0].rows) {
          row.hidden = !matches(row);
          shown ||= !row.hidden;
        }
        holder(table).hidden = !shown;
        const title = heading(table);
        if (title && title.tagName === 'H3') title.hidden = !shown;
      }
      // A section heading shows while any table under it does.
      for (const title of content.querySelectorAll('h2')) {
        let node = title.nextElementSibling;
        let any = false;
        let tabled = false;
        while (node && node.tagName !== 'H2') {
          const table = node.matches('table') ? node : node.querySelector && node.querySelector('table');
          if (table && tables.includes(table)) {
            tabled = true;
            any ||= !holder(table).hidden;
          }
          node = node.nextElementSibling;
        }
        if (tabled) title.hidden = !any;
      }
      const query = new URLSearchParams(location.search);
      for (const select of selectors) {
        if (select.value) query.set(select.dataset.featureFilter, select.value);
        else query.delete(select.dataset.featureFilter);
      }
      const search = query.toString();
      history.replaceState(null, '', location.pathname + (search ? '?' + search : '') + location.hash);
    }
    const query = new URLSearchParams(location.search);
    for (const select of selectors) {
      const value = query.get(select.dataset.featureFilter);
      if (value && [...select.options].some(option => option.value === value)) select.value = value;
    }
    bar.addEventListener('change', update);
    bar.addEventListener('input', update);
    bar.querySelector('[data-feature-reset]').addEventListener('click', () => {
      search.value = '';
      for (const select of selectors) select.value = '';
      update();
      search.focus();
    });
    update();
  }
  // Tables with the same header row on one page share one fixed column split, so their columns line up down the page
  // (owner, 2026-11-09): each column takes the widest share it has in any of them.
  function alignTables() {
    const content = document.querySelector('.md-content .md-typeset');
    if (!content) return;
    const groups = new Map();
    for (const table of content.querySelectorAll('table')) {
      if (table.dataset.aligned || !table.tHead || !table.tHead.rows.length || !table.offsetWidth) continue;
      const key = [...table.tHead.rows[0].cells].map(cell => cell.textContent.trim()).join('\u0001');
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(table);
    }
    for (const tables of groups.values()) {
      if (tables.length < 2) continue;
      const shares = [];
      for (const table of tables) {
        const cells = [...table.tHead.rows[0].cells];
        const total = table.getBoundingClientRect().width || 1;
        cells.forEach((cell, index) => {
          shares[index] = Math.max(shares[index] || 0, cell.getBoundingClientRect().width / total);
        });
      }
      const sum = shares.reduce((a, b) => a + b, 0) || 1;
      for (const table of tables) {
        table.querySelector(':scope > colgroup')?.remove();
        const columns = document.createElement('colgroup');
        for (const share of shares) {
          const column = document.createElement('col');
          column.style.width = `${(100 * share / sum).toFixed(3)}%`;
          columns.append(column);
        }
        table.prepend(columns);
        table.style.tableLayout = 'fixed';
        table.dataset.aligned = 'true';
      }
    }
  }
  function setupAll() {
    setup();
    alignTables();
    setupFeatures();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', setupAll);
  else setupAll();
  if (typeof document$ !== 'undefined') document$.subscribe(setupAll);
})();
