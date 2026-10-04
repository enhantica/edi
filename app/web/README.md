# EasyDiffraction in the browser

This folder is the EasyDiffraction app built for WebAssembly: a static site. Copy it to any web host and open
`index.html` (for example `https://enhantica.github.io/edi/webapp/`).

## What is in it

- `index.html`: the start page. It loads the multithreaded build when the browser allows it, else the
  single-thread build. `?build=multithread` or `?build=singlethread` forces one.
- `multithread-<hash>/`: the app with its calculation worker on a thread of its own.
- `singlethread-<hash>/`: the app with no threads. A calculation or a fit runs on the page's own thread, so the page
  does not respond until it finishes.
- `mark.svg`, `name.svg`, `splash.css`: the splash, the mark turning while the app loads; `logo.svg`: the logo,
  still; the `-dark` files are the same in the dark colour scheme, which the page takes from the app's settings.
- `build.json`: names the two build folders. Each folder is named by a hash of its files, so a new build never
  replaces an old one's files at the same address: unpack a new zip over the old site and the page loads the new
  build, whatever the browser cached. The old folders can be deleted.
- `coi-serviceworker.js`: adds the two headers the multithreaded build needs on hosts that do not send them.
- `BUILD-INFO.txt`: the versions it was built from and the size of each build.
- `LICENSES/`: the licence texts.

## Hosting requirement

The multithreaded build needs a cross-origin-isolated page, which takes two response headers:

```
Cross-Origin-Opener-Policy: same-origin
Cross-Origin-Embedder-Policy: require-corp
```

A host that lets you set headers (Netlify or Cloudflare Pages through a `_headers` file, a web server's
configuration) can send them for the whole folder. A host that cannot, such as GitHub Pages, needs nothing
more: on the first visit the start page registers `coi-serviceworker.js`, which adds the headers, and
reloads itself once. A service worker needs HTTPS (or `localhost`); where it cannot run, the page loads the
single-thread build. Opening `index.html` straight from the disk (`file://`) does not work: browsers do not
load WebAssembly that way. To try the folder locally, serve it, for example with `python -m http.server`
inside it, and open `http://localhost:8000/`.

## Files

In the browser the app keeps its files in the page's memory. *Open an existing project* asks for a project
folder, as the desktop app does; the browser copies its files into the page (it may ask to confirm the upload).
A project saves as a `.zip` archive of its folder, downloaded by the browser: unpack it to open it again. The settings are kept in the browser's local storage.

## Licence

The app links Qt (LGPL-3.0) and Qt Graphs (GPL-3.0), so this build of the app is distributed under the GNU
General Public License v3 (`LICENSES/COPYING`, also `LICENSES/GPL-3.0.txt`). EasyDiffraction's own source
code is BSD 3-Clause (`LICENSES/LICENSE`). `LICENSES/THIRD-PARTY-NOTICES` and `LICENSES/DEPENDENCIES.md` list
every component with its licence; `coi-serviceworker.js` is MIT (`LICENSES/coi-serviceworker-MIT.txt`).
