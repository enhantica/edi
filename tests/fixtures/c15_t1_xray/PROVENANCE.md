# LiF single-wavelength independent reference

`generate.py` reads committed diffraction-lib bytes at the full SHA in
`manifest.json`. It extracts the calculated column of the IGOR `.prf`, never
observed dummy intensities. No gate runs FullProf. `model.edi` is a transcription
of `lif_single_unpolarized.pcr`: fixed parameters, chemical occupancies one
(FullProf special-position occupancy is 1/48), no fit or scale adjustment.

The native full-pattern bound is a provisional 1% relative L2 acceptance bound,
matching the existing fixed-parameter  FullProf cases. It is not a measured
engine regression pin; a physical-convention discrepancy must be resolved and
reported rather than silently fitting the scale. The page banks its own tighter
measured bounds after implementation. Cthm=0 and Rpolarz=0 in this reference;
monochromator polarization belongs to .

LP convention reference: FullProf manual section 3.4,
https://www.ill.eu/sites/fullprof/downloads/Docs/FullProf_Manual.pdf .
