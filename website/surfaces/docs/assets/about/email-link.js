// SPDX-License-Identifier: BSD-3-Clause
/* An e-mail address kept out of the page's HTML, so address harvesters do not find it: each `.ed-email` element holds
   it encoded (base64 of the address reversed) and gets a "Show e-mail" link, which shows the address as a mailto: link
   when clicked. Without JavaScript the element's noscript text stays. */
(() => {
  function setup() {
    for (const holder of document.querySelectorAll('.ed-email[data-mail]')) {
      if (holder.dataset.ready) continue;
      holder.dataset.ready = 'true';
      const link = document.createElement('a');
      link.href = '#';
      link.textContent = holder.dataset.label || 'Show e-mail';
      link.addEventListener('click', event => {
        if (link.dataset.shown) return;
        event.preventDefault();
        const address = atob(holder.dataset.mail).split('').reverse().join('');
        link.href = `mailto:${address}`;
        link.textContent = address;
        link.dataset.shown = 'true';
      });
      holder.append(link);
    }
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', setup);
  else setup();
  if (typeof document$ !== 'undefined') document$.subscribe(setup);
})();
