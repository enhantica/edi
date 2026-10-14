# Independent axial Gaussian reference

`reference.py` evaluates Bragg's law, a normalized Gaussian and the neutron
powder Lorentz factor directly. The fixture declares wavelength 1.54 Å,
Gaussian FWHM 0.05 degrees, zero Lorentz width and zero ADP. Two coincident
La sites have occupancies summing to one. The coherent La scattering length
8.24 fm comes from the [NIST neutron table](https://www.ncnr.nist.gov/resources/n-lengths/list.html)
(Neutron News 3(3), 1992, pp. 29–37); the exact fm²-to-barn factor is 0.01.

Each phase has two axial Friedel orbits with multiplicity two and equal |F|².
Their different peak windows do not overlap. The declared one-sided cutoff is
five FWHM (0.25 degrees), with a cosine taper over its outer 20 percent.
The masks used to author observations extend to 0.27 degrees and contain
those entire windows. The scalar closed form supplies each reflection's
unrounded profile, including tails too small to recover by subtracting a
background from a total calculated pattern.

Observed reflection intensities use the measured-minus-background rows
partitioned by those profiles over the actual calculated-minus-background
array. That array is an input to the factor definition, not an independent
expected factor. For a saved scan, it must belong to the selected template
row, including floating-point background addition and subtraction. Neither
reported phase factor is used to construct its expected value.
