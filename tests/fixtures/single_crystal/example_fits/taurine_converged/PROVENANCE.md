# Converged taurine fitting reference

FullProf.2k 8.40 (Feb2026-ILL JRC), run 2026-10-24 at 14:20:11 CEST
(12:20:11 UTC), imported without executing FullProf again.

The owner supplied SENJU_taurine/taurine.pcr and taurine.int on 2026-10-23.
`original.pcr` preserves that input byte for byte. `input.pcr` changes only its
NCY/Eps line from 20 / 0.10 to 200 / 0.01. Every observation byte is unchanged.
`taurine.pcr` is the control file rewritten by FullProf AFTER fitting; it is
preserved as output and must not be mistaken for the starting input.
The complete .out, .sum and .prf are independent engine outputs. No earlier
verification or fitting reference is replaced.

The output explicitly converges at cycle 52 with 135 independent parameters
and 947 selected reflections. The summary prints Chi2 30.1 and RF2w 12.2 percent.
The trailing Fortran EOF in run.log occurs at the continuation prompt AFTER
all outputs were written. It is retained, never represented as an exit-zero run.

The reference writer parses final high-precision parameters from .out and
codewords from original.pcr. FullProf manual equations 3.7 and 3.8 define the
codeword coefficient in sigma and the N-p denominator. Scales and extinction
have coefficient 0.20; positions and beta components have coefficient 1.00.
Reported sigma and conventional sigma are both retained. Beta targets use the
final parameter list directly, avoiding the summary's displayed x10000 units.
The headline Chi2 and the independently summed selected Dif/sig objective are
retained separately; their difference is not hidden by changing the divisor.

The project is the committed six-dataset taurine fitting example, copied only
as input stimulus. No fitted product value supplies a target or an uncertainty.
`reference.json` pins all source, output and project hashes. This writer never
runs fp2k. No other reference quantity or bound is changed.
