# Licences and third-party components

edi's source code, the application's included, is licensed under the [BSD 3-Clause License](LICENSE).
The EasyDiffraction application built from it is distributed under the
[GNU General Public License version 3](COPYING), because it links Qt Graphs, Qt Quick 3D and Qt Shader
Tools, which are available under that licence only ([app/DISTRIBUTION-LICENSE.md](app/DISTRIBUTION-LICENSE.md)).

The components below are linked into, bundled with, or compiled into the application, the Python package or
both. Their licence texts are in [THIRD-PARTY-NOTICES](THIRD-PARTY-NOTICES), which the application also
bundles and shows in its About window; the Python package carries the binding licences in
[licenses/](licenses/).

## Engine and libraries

| Component | Version | Licence | In edi |
| --- | --- | --- | --- |
| crysta |  | BSD-3-Clause | the diffraction engine, statically linked into the application and the Python extension |
| SLEEF | 3.9.0 | BSL-1.0 | vectorised mathematical functions, through crysta |
| Eigen | 3.4.0 | MPL-2.0 | linear algebra headers, compiled into crysta and edi |
| libgomp | 15.2.0 | GPL-3.0-only WITH GCC-exception-3.1 | the GCC OpenMP runtime (Linux), with the GCC runtime libraries libstdc++ and libgcc_s, under the GCC Runtime Library Exception |
| llvm-openmp | 23.1.2 | Apache-2.0 WITH LLVM-exception | the LLVM OpenMP runtime (macOS) |
| nanobind | 2.13.0 | BSD-3-Clause | the Python bindings, compiled into the Python extension |
| robin-map |  | MIT | the hash map inside nanobind, compiled into the Python extension |

## Application framework

| Component | Version | Licence | In edi |
| --- | --- | --- | --- |
| Qt | 6.11.2 | LGPL-3.0-only | the application framework: Qt Core, Qt GUI, Qt QML, Qt Quick, Qt Quick Controls and the modules they load |
| Qt Graphs | 6.11.2 | GPL-3.0-only | the pattern chart; linking it makes the distributed application a GPL-3.0 work (COPYING) |
| Qt Quick 3D | 6.11.2 | GPL-3.0-only | the structure view's 3D scene, and the 3D module Qt Graphs loads; GPL-3.0 (COPYING) |
| Qt Shader Tools | 6.11.2 | GPL-3.0-only | the shader tooling Qt Quick 3D uses; GPL-3.0 (COPYING) |
| EasyScience gui-components |  | BSD-3-Clause | the base QML components and styles of the application |
| easydiffractionbeta |  | BSD-3-Clause | the application design and QML the application is ported from, and the Jmol element colours and radii in the element table |
| diffraction-lib |  | BSD-3-Clause | the Python API design edi follows, example data, and the element colour and radius table |
| pymatgen |  | MIT | VESTA element colours and Shannon ionic radii in the element table, compiled into edi |

## Libraries Qt links (application builds)

| Component | Version | Licence | In edi |
| --- | --- | --- | --- |
| ICU | 78.3 | Unicode-3.0 | Unicode and locale support |
| HarfBuzz | 14.5.0 | MIT | text shaping |
| FreeType | 2.14.3 | FTL | font rendering, used under the FreeType License (with its acknowledgement below) |
| libpng | 1.6.58 | libpng-2.0 | PNG images |
| zlib | 1.3.2 | Zlib | compression |
| PCRE2 | 10.47 | BSD-3-Clause WITH PCRE2-exception | regular expressions |
| zstd | 1.5.7 | BSD-3-Clause | compression |
| Brotli | 1.2.0 | MIT | compression |
| OpenSSL | 3.6.4 | Apache-2.0 | cryptography for network access |
| Expat | 2.8.5 | MIT | XML parsing |
| Graphite2 | 1.3.15 | LGPL-2.1-or-later OR MPL-2.0 OR GPL-2.0-or-later | font shaping, through HarfBuzz |
| double-conversion | 3.4.0 | BSD-3-Clause | number formatting |
| libjpeg-turbo | 3.2.0 | IJG AND BSD-3-Clause AND Zlib | JPEG images |
| LibTIFF | 4.7.2 | libtiff | TIFF images |
| libwebp | 1.6.0 | BSD-3-Clause | WebP images |
| GLib | 2.90.0 | LGPL-2.1-or-later | the event loop integration (Linux) |
| D-Bus | 1.16.2 | AFL-2.1 OR GPL-2.0-or-later | desktop integration (Linux), used under AFL-2.1 |
| Fontconfig | 2.18.3 | MIT | font discovery (Linux) |
| libxcb | 1.17.0 | MIT | the X11 platform plugin (Linux) |
| libxkbcommon | 1.13.2 | MIT | keyboard handling (Linux) |
| Wayland | 1.26.0 | MIT | the Wayland platform plugin (Linux) |
| libdrm | 2.4.129 | MIT | graphics device access (Linux) |
| libglvnd | 1.7.0 | MIT-style (libglvnd) | OpenGL dispatch (Linux) |
| MIT Kerberos | 1.22.2 | MIT-style | network authentication (Linux) |

## Fonts

| Component | Version | Licence | In edi |
| --- | --- | --- | --- |
| PT Sans, PT Mono |  | OFL-1.1 | interface fonts, bundled |
| Noto Sans, Noto Sans Mono |  | OFL-1.1 | interface fonts, bundled |
| Baloo 2 |  | OFL-1.1 | the wordmark font, bundled |
| Font Awesome Free |  | OFL-1.1 AND CC-BY-4.0 | icons: the font under OFL-1.1, the icon designs under CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/) |

## Acknowledgements

Portions of this software are copyright © 2026 The FreeType Project (https://freetype.org). All rights reserved.

The facility data credits are listed in [THIRD-PARTY-NOTICES](THIRD-PARTY-NOTICES).
