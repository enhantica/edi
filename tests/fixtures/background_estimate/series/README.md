# Known-order series inputs

These are independent closed-form cubic backgrounds `[50,12,-5,7]`, in powers of
`x/47.125-1` or the Chebyshev coordinate over [17,86]. The 1025-point grid covers
[20,80]. A specified 32-bit LCG, seed `0xC34B28`, adds bounded noise ±0.1, and five
Gaussian peaks (height 100, sigma 0.15) are well separated. No product output defines
an expected coefficient or count.

`controls.json` records NumPy 2.5.2, pybaselines 1.2.1 and the repo-relative authoring
command for `generate_known.py`. These tools run once outside the product tree and
are not test dependencies. Independent arPLS (lambda 1000, width 6) first meets twice
the MAD noise at four terms. Coefficient bias is below 0.075; the test allowance 0.3
covers four times that bias while distinguishing every nonconstant coefficient.
The deliberately insufficient two-term cap must stop at two. Native comparisons
also use the committed corpus Stage-1 curves and independent FullProf references.

The generated app inputs use legacy `false` (canonical `ignore`) to isolate series
estimation from policy migration; all three canonical choices have separate gates.

The known-cubic noise header uses diffraction-lib’s declared factor 1.4826 times
the second-difference MAD divided by sqrt(6). Before, the author script used the
full normal quantile reciprocal (about 1.4826022185), which differed at about
1e-7 counts and could not meet a 1e-12 equality check. The convention is now
identical to the independent method source; the cubic samples, coefficient
bounds (0.3), four-term recovery and two-term cap stay unchanged. The authoring
receipt records the actual NumPy and pybaselines versions.
