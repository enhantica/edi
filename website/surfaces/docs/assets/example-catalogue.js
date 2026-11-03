/* Filter the generated native catalogue; unenhanced HTML retains every example. */
(() => {
  function setup() {
    document.querySelectorAll('[data-example-catalogue]').forEach(catalogue => {
      if (catalogue.dataset.ready) return;
      catalogue.dataset.ready = 'true';
      const rows = [...catalogue.querySelectorAll('[data-example-row]')];
      const search = catalogue.querySelector('[data-example-search]');
      const selectors = [...catalogue.querySelectorAll('[data-example-filter]')];
      function update() {
        const words = search.value.toLocaleLowerCase().trim().split(/\s+/).filter(Boolean);
        let count = 0;
        for (const row of rows) {
          const matches = words.every(word => row.dataset.search.includes(word)) && selectors.every(select =>
            !select.value || JSON.parse(row.getAttribute('data-' + select.dataset.exampleFilter.toLowerCase())).includes(select.value));
          row.hidden = !matches;
          count += Number(matches);
        }
        catalogue.querySelector('[data-example-count]').textContent = `${count} of ${rows.length} examples`;
      }
      catalogue.addEventListener('input', update);
      catalogue.addEventListener('change', update);
      update();
    });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', setup);
  else setup();
  if (typeof document$ !== 'undefined') document$.subscribe(setup);
})();
