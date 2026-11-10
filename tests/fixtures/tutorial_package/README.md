The reference.json outline was read from diffraction-lib's published script at the
source URL and digest in that file. The workflow test adapts its structure, atom
sites, wavelength and profile settings. It uses the existing measured LBCO data
and checks a decreasing weighted residual, without claiming fitted-value accuracy.
The exact system-test file is registered against lbco-hrpt-s2 in fit-sites.yml.
It reads that corpus measurement and sets the public Wyckoff letters from the
corpus structure, while constructing the project in code. The fit policy stays
unchanged; no synthetic project origin is assigned.
The future case pins are regression pins, never independent correctness values.

The package gates cover the public import, metadata, setup cells, empty named
projects, explicit structure links and the per-step display operations. The
workflow is kept separate so a missing display cannot hide a construction defect.
A fallback to the legacy import lets the empty-project gates reach the current
model; the separate public-import gate still requires easydiffraction.

Fresh-environment installation and display/report rendering equivalence remain
runtime work once the package wheel producer and display interface are available.
