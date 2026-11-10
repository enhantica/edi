/* Subtle audience switcher: a small fixed control, bottom-right,
   linking the user and developer halves of the site — modelled on the unobtrusive
   corner control at docs.easydiffraction.org/lib/latest/. */
(function () {
  function base() {
    var path = window.location.pathname;
    var m = path.match(/^(.*?)\/(user|dev)(\/|$)/);
    return m ? { root: m[1], side: m[2] } : null;
  }
  var here = base();
  if (!here) return;
  var other = here.side === 'user' ? 'dev' : 'user';
  var label = here.side === 'user' ? 'Developer docs' : 'User docs';
  var a = document.createElement('a');
  a.className = 'audience-switcher';
  a.href = here.root + '/' + other + '/';
  a.textContent = label;
  a.title = 'Switch audience';
  document.body.appendChild(a);
})();
