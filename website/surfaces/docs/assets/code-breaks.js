// SPDX-License-Identifier: BSD-3-Clause
// Inline code never breaks inside a word (the owner, 2026-11-10): each run of it between break points is kept whole,
// and a long dotted path may break after '.', '_' or '[', where a <wbr> goes. On every page the site shows.
(() => {
  const BREAK = /([._[])/;
  const mark = root => {
    for (const code of root.querySelectorAll('.md-typeset code:not(pre code):not([data-breaks])')) {
      code.dataset.breaks = '';
      const walker = document.createTreeWalker(code, NodeFilter.SHOW_TEXT);
      const texts = [];
      while (walker.nextNode()) texts.push(walker.currentNode);
      for (const text of texts) {
        // Each run between break points stays whole (a no-wrap span); a line may break only at a space or after '.',
        // '_' or '[' (a <wbr>), never at a hyphen or inside a word.
        const parts = text.data.split(/([._[]| +)/);
        const fragment = document.createDocumentFragment();
        for (const part of parts) {
          if (!part) continue;
          if (/^ +$/.test(part)) {
            fragment.append(part);
          } else if (part.length === 1 && BREAK.test(part)) {
            fragment.append(part, document.createElement('wbr'));
          } else {
            const run = document.createElement('span');
            run.className = 'ed-code-run';
            run.textContent = part;
            fragment.append(run);
          }
        }
        text.replaceWith(fragment);
      }
    }
  };
  if (typeof document$ !== 'undefined') document$.subscribe(() => mark(document));
  else document.addEventListener('DOMContentLoaded', () => mark(document));
})();
