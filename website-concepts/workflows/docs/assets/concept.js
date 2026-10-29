(function () {
  function addContributorLink() {
    var footer = document.querySelector('.md-footer-meta__inner');
    if (!footer || footer.querySelector('.ed-footer-link')) return;
    var link = document.createElement('a');
    link.className = 'ed-footer-link';
    link.href = 'https://enhantica.github.io/edi/dev/';
    link.textContent = 'Contributor documentation ↗';
    footer.appendChild(link);
  }
  addContributorLink();
  if (typeof document$ !== 'undefined') document$.subscribe(addContributorLink);
})();
