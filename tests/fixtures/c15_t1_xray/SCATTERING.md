#  scattering selector test seam

The owner decision at development hub fd2ab3bad retires `lab-kalpha`; it is now tested only
as a refused unknown name, never an alias. The dispersion sources are
`cromer-liberman` (default), `sasaki1989`, `it1992`, and `none`.
The f0 selector remains independently `wk1995` (default) or `it1992`.

`generate_named_dispersion.py` reads the external cctbx `reference/sasaki`
`fpwide.tbl` and `fpk.tbl`, distributed in libraries commit
`57d1cf5fcad9ba4fd86224eb4047af35214766cd`. The required citation is S. Sasaki
(1989), *Numerical Tables of Anomalous Scattering Factors Calculated by the
Cromer and Liberman Method*, KEK Report 88-14, 1–136 (its README).
The exact-grid Li/F/Fe components and Fe quarter-interval witnesses are pinned
with the source digests in `named_dispersion.json`. Interpolation follows the
committed ADR-0066 continuous rule: f-prime linear in log energy, f-double-prime
log-log. The explicit Fe K edge is 1.74346 Angstrom; the refusal witness 1.74345
lies in its 1.7434–1.7435 fine-grid interval. Neither a missing source nor an
unknown-name rejection alone proves edge handling; the positive independent
Sasaki-value gate must also pass.

IT1992 dispersion comes from International Tables Vol C, Table 4.2.6.8,
printed p.255 (PDF page 283), Creagh & McAuley. The held physics PDF and revision
are recorded in `named_dispersion.json`. Its ten Fe f-prime/f-double-prime
pairs are transcribed in the visible generator. Signs were checked against the
rendered PDF, because pdftotext drops minus signs: the five longest wavelengths
have negative Fe f-prime; the five shortest have positive values. This direct
signed transcription is the independent test carrier, not any product table.
All ten lines are checked, and off-line lookup must refuse. Committed ADR-0066
(`cec16933`) sets the IT1992 tolerance to 0.003 Angstrom; probes on both sides
inside and outside that boundary replace the retired table's 0.01 boundary. The profile oracle
uses the same independently tabulated components in a closed-form single-site
complex intensity, with no fitted quantity.

The f0 sources are unchanged: CrysFML2008's IT1992 coefficient transcription in
`crysfml2008/Src/CFML_Tables/Tab_Set_ScatterT.f90` (the libraries revision above),
and Waasmaier–Kirfel A51 (1995), DOI 10.1107/S0108767394013292, distributed in
DABAX `f0_WaasKirf.dat` through the independent periodictable copy. No correctness
oracle imports crysta or reads its output. The LiF profile oracle remains the
pinned FullProf output with the original 1 percent bound; its experiment now
explicitly declares IT1992 f0 plus Sasaki1989 dispersion.

## Continuous default (owner scope amendment, development hub 67ce27955)

`cromer-liberman` is the default dispersion source, as amended ADR-0066 specifies.
The visible `generate_dispersion_probe.py` extracts independent DABAX/FPRIME 3F
plus Kissel-Pratt Fe rows from the external rietx distribution, pinned in
`cromer_liberman_fe.json` by libraries commit and SHA-256. It never imports either
product. Two quarter-interval probes between 10000.7 and 10042.2 eV discriminate
the ADR's f-prime linear-in-log-energy / f-double-prime log-log interpolation from a nearest-row snap. The Fe-edge witness lies between
7087.2 and 7116.67 eV, where f-double-prime jumps from 0.470698 to 3.94646;
2900 and 71000 eV exercise both outside-range refusals. Those values are copied
from the independent source or derived by that generator using exact SI h\*c/e.
