# Independent single-crystal pattern inputs

The P1 structure has one cobalt atom at the origin with unit occupancy and zero displacement. Its orthorhombic cell
is 4.3, 5.1 and 6.7 Å. The magnetic variant has a 2 μB moment along c and the Co²⁺ Brown form factor with no j₂ term.
The four measured reflections are explicit inputs, including one parallel to the moment, whose perpendicular magnetic
contribution vanishes.

[generate.py](generate.py) writes these inputs and `reference.json` without importing the app. It uses the reciprocal
cell metric, Sears (1992) b(Co) = 2.4900 fm, Brown's Co²⁺ coefficients from the supplied engine source's committed data,
and the CODATA 2018 magnetic-moment and electron-radius constants. F² is expressed in 10⁻²⁴ cm²; 1 fm = 0.1 × 10⁻¹² cm.
For an unpolarised beam, nuclear and perpendicular magnetic F² add. The independent squared nuclear and total
intensities remain N and T in `reference.json`. [ADR-0090](../../../docs/dev/adrs/0090-pattern-x-axes.md) defines the
F display: the total is √T and the nuclear boundary is √T × N/T, with the magnetic segment above it. The F² display
uses N and T directly. Bar and thin-line expectations apply this display convention to the unchanged physical references;
a zero total has a zero boundary.

`powder-colours.json` uses the immutable published powder palettes and their checked release-data hash through the
existing chart-controls generator. The legacy `main` preference token selects the published Main palette; named future
palette tokens use the separate owner-approved palette reference. These are display references, separate from the
unchanged scientific reflection values.

The data-free input explicitly sets a 0.35 Å⁻¹ sinθ/λ resolution limit, within
1/λ for the declared wavelength. Counterfactual witnesses reuse the same physical
reference with a moment alias, a fixed `mz = 2` relation, or `mz = 1 + 1`.
They inspect the real plotted nuclear and magnetic strokes and require the original
moment, alias and constraint rows to survive the nuclear-only calculation unchanged.
