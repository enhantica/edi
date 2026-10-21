# Licences and third-party components

edi's source code, the application's included, is licensed under the [BSD 3-Clause License](LICENSE).
The EasyDiffraction application built from it is distributed under the
[GNU General Public License version 3](COPYING), because it links Qt Graphs, Qt Quick 3D and Qt Shader
Tools, which are available under that licence only ([app/DISTRIBUTION-LICENSE.md](app/DISTRIBUTION-LICENSE.md)).

This file is the one list of the third-party components edi ships. Each surface has its own column: the desktop
application, the web application (its site), the Python package and the `easydiffraction` command-line binary (today a
stub that prints the core's version, so it carries only the C++ runtime). A cell
says how that surface carries the component: linked, bundled (shipped as a file beside or inside it) or compiled in;
`—` means it does not carry it. A version in a cell is that surface's own, where it differs from the Version column.
Each surface lists only its own column: the application's About window reads this file from its resources, and
`tools/licences/sync.py` writes the Python package's [licenses/](licenses/) from it. The licence texts are in
[THIRD-PARTY-NOTICES](THIRD-PARTY-NOTICES), one section per component.

## Engine and libraries

| Component | Version | Licence | Desktop app | Web app | Python package | CLI | In edi |
| --- | --- | --- | --- | --- | --- | --- | --- |
| crysta |  | BSD-3-Clause | linked | linked | linked | — | the diffraction engine, statically linked |
| SLEEF | 3.9.0 | BSL-1.0 | linked | compiled in | linked | — | vectorised mathematical functions, through crysta |
| Eigen | 3.4.0 | MPL-2.0 | compiled in | compiled in | compiled in | — | linear algebra headers, compiled into crysta and edi |
| libgomp | 15.2.0 | GPL-3.0-only WITH GCC-exception-3.1 | linked | — | linked | linked | the GCC OpenMP runtime (Linux), with the GCC runtime libraries libstdc++ and libgcc_s, under the GCC Runtime Library Exception |
| llvm-openmp | 23.1.2 | Apache-2.0 WITH LLVM-exception | linked | — | linked | — | the LLVM OpenMP runtime (macOS) |
| nanobind | 2.13.0 | BSD-3-Clause | — | — | compiled in | — | the Python bindings, compiled into the Python extension |
| robin-map |  | MIT | — | — | compiled in | — | the hash map inside nanobind, compiled into the Python extension |
| Emscripten runtime | 4.0.7 | MIT AND Apache-2.0 WITH LLVM-exception | — | compiled in | — | — | the C and C++ runtime of the web build (Emscripten's libc from musl, libc++ and libc++abi from LLVM) |

## Application framework

| Component | Version | Licence | Desktop app | Web app | Python package | CLI | In edi |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Qt | 6.11.2 | LGPL-3.0-only | linked | compiled in | — | — | the application framework: Qt Core, Qt GUI, Qt QML, Qt Quick, Qt Quick Controls and the modules they load |
| Qt Graphs | 6.11.2 | GPL-3.0-only | linked | compiled in | — | — | the pattern chart; linking it makes the distributed application a GPL-3.0 work (COPYING) |
| Qt Quick 3D | 6.11.2 | GPL-3.0-only | linked | compiled in | — | — | the structure view's 3D scene, and the 3D module Qt Graphs loads; GPL-3.0 (COPYING) |
| Qt Shader Tools | 6.11.2 | GPL-3.0-only | linked | compiled in | — | — | the shader tooling Qt Quick 3D uses; GPL-3.0 (COPYING) |
| EasyScience gui-components |  | BSD-3-Clause | compiled in | compiled in | — | — | the base QML components and styles of the application |
| pymatgen |  | MIT | compiled in | compiled in | compiled in | — | VESTA element colours and Shannon ionic radii in the element table, compiled into edi |
| coi-serviceworker | 0.1.7 | MIT | — | bundled | — | — | the service worker that lets the web app use threads on a host without the needed headers |

## HTML report libraries

A saved HTML report loads these from their pinned web addresses, or carries them when the report embeds its chart
libraries: the desktop app keeps them in its resources and the web app on its site. The vendored copies are in
`data/report/vendor/`, unchanged from the npm releases.

| Component | Version | Licence | Desktop app | Web app | Python package | CLI | In edi |
| --- | --- | --- | --- | --- | --- | --- | --- |
| plotly.js | 3.7.0 | MIT | bundled | bundled | — | — | the report's pattern charts: `plotly-cartesian.min.js` of `plotly.js-cartesian-dist-min` |
| three.js | 0.160.0 | MIT | bundled | bundled | — | — | the report's structure views: `build/three.module.min.js` and `examples/jsm/controls/OrbitControls.js` of `three` |

| Vendored file | From the npm tarball (registry integrity) | sha256 |
| --- | --- | --- |
| `plotly-cartesian-3.7.0.min.js` | `plotly.js-cartesian-dist-min-3.7.0.tgz` (`sha512-kfQjcAXXByRlskP8JsrlGYRPOvB+kOehZk/qBNewgr9SOMEnBN5nwEnUGOAQ0EEgYdQX51z3VZ81aBnDgSr9Bw==`) | `7c593b9eda0e74a1d07335cf89cbf7a55ffc114909980c3729af835453bdb02a` |
| `three-0.160.0.module.min.js` | `three-0.160.0.tgz` (`sha512-DLU8lc0zNIPkM7rH5/e1Ks1Z8tWCGRq6g8mPowdDJpw1CFBJMU7UoJjC6PefXW7z//SSl0b2+GCw14LB+uDhng==`) | `3e690ac7d180b0aadf0891bea39eec643e29e2d3e75c99b18689518665f69ba6` |
| `three-0.160.0-OrbitControls.js` | `three-0.160.0.tgz`, as above | `5a44a9e86a2a0fb11933eed69bc2cd33c76a496854c1aed6ed776efa87d7b064` |

## Libraries Qt links

The desktop app links these as shared libraries; the web build compiles Qt's own copies of some of them into Qt.

| Component | Version | Licence | Desktop app | Web app | Python package | CLI | In edi |
| --- | --- | --- | --- | --- | --- | --- | --- |
| ICU | 78.3 | Unicode-3.0 | linked | — | — | — | Unicode and locale support |
| HarfBuzz | 14.5.0 | MIT | linked | compiled in, through Qt (14.3.0) | — | — | text shaping |
| FreeType | 2.14.3 | FTL | linked | compiled in, through Qt | — | — | font rendering, used under the FreeType License (with its acknowledgement below) |
| libpng | 1.6.58 | libpng-2.0 | linked | compiled in, through Qt | — | — | PNG images |
| zlib | 1.3.2 | Zlib | linked | compiled in, through Qt | — | — | compression |
| PCRE2 | 10.47 | BSD-3-Clause WITH PCRE2-exception | linked | compiled in, through Qt | — | — | regular expressions |
| zstd | 1.5.7 | BSD-3-Clause | linked | — | — | — | compression |
| Brotli | 1.2.0 | MIT | linked | — | — | — | compression |
| OpenSSL | 3.6.4 | Apache-2.0 | linked | — | — | — | cryptography for network access |
| Expat | 2.8.5 | MIT | linked | — | — | — | XML parsing |
| Graphite2 | 1.3.15 | LGPL-2.1-or-later OR MPL-2.0 OR GPL-2.0-or-later | linked | — | — | — | font shaping, through HarfBuzz |
| double-conversion | 3.4.0 | BSD-3-Clause | linked | compiled in, through Qt | — | — | number formatting |
| libjpeg-turbo | 3.2.0 | IJG AND BSD-3-Clause AND Zlib | linked | compiled in, through Qt | — | — | JPEG images |
| LibTIFF | 4.7.2 | libtiff | linked | — | — | — | TIFF images |
| libwebp | 1.6.0 | BSD-3-Clause | linked | — | — | — | WebP images |
| GLib | 2.90.0 | LGPL-2.1-or-later | linked | — | — | — | the event loop integration (Linux) |
| D-Bus | 1.16.2 | AFL-2.1 OR GPL-2.0-or-later | linked | — | — | — | desktop integration (Linux), used under AFL-2.1 |
| Fontconfig | 2.18.3 | MIT | linked | — | — | — | font discovery (Linux) |
| libxcb | 1.17.0 | MIT | linked | — | — | — | the X11 platform plugin (Linux) |
| libxkbcommon | 1.13.2 | MIT | linked | — | — | — | keyboard handling (Linux) |
| Wayland | 1.26.0 | MIT | linked | — | — | — | the Wayland platform plugin (Linux) |
| libdrm | 2.4.129 | MIT | linked | — | — | — | graphics device access (Linux) |
| libglvnd | 1.7.0 | MIT-style (libglvnd) | linked | — | — | — | OpenGL dispatch (Linux) |
| MIT Kerberos | 1.22.2 | MIT-style | linked | — | — | — | network authentication (Linux) |

## Fonts

| Component | Version | Licence | Desktop app | Web app | Python package | CLI | In edi |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PT Sans, PT Mono |  | OFL-1.1 | bundled | bundled | — | — | interface fonts, bundled |
| Encode Sans |  | OFL-1.1 | bundled | bundled | — | — | fit summary arrow, bundled |
| Noto Sans, Noto Sans Mono |  | OFL-1.1 | bundled | bundled | — | — | interface fonts, bundled |
| Baloo 2 |  | OFL-1.1 | bundled | bundled | — | — | the wordmark font, bundled |
| Font Awesome Free |  | OFL-1.1 AND CC-BY-4.0 | bundled | bundled | — | — | icons: the font under OFL-1.1, the icon designs under CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/); seven designs also draw the HTML report's structure view buttons |

## Acknowledgements

Portions of this software are copyright © 2026 The FreeType Project (https://freetype.org). All rights reserved.

edi's Python API follows the design of diffraction-lib (BSD-3-Clause, https://github.com/easyscience/diffraction-lib),
whose element table and example data edi took over; of the element table's sources, pymatgen is listed above, and its
Jmol colours and radii are scientific values that carry no notice.

The facility data credits are listed in [THIRD-PARTY-NOTICES](THIRD-PARTY-NOTICES).
