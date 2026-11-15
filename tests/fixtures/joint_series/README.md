# Joint series references

The small routing series has three points and two experiments. Its cell lengths and scales are authored in
`cases.py`; forward calculation creates observations from those inputs. Recovering those inputs is a round-trip
invariant, not an external intensity reference. Its experiment order differs from the data filenames' order, and
`0007` and `07` are distinct point keys. No fitted output supplies an expected value.

The ratio witness has two identical phases, so their occupied unit-cell masses and volumes cancel. For leader
scales `u=2`, `v=1` and member scales `t=3`, `t*v/u`, the second fraction is `v/(u+v)`. Uncertainty only in `t`
contributes zero variance. With `sigma(u)=0.04`, `sigma(v)=0.03`, `rho=0.5`, the quotient gradient is `(-1/9,2/9)`.
This is the Hill–Howard equation composed with the declared relation, using ordinary covariance propagation.

The moment witness uses the direct-axis unit vectors, Cartesian x along a and z along c*, polar angle from +z,
and azimuth from +x. Its monoclinic cell, signed components and supplied full covariance are authored inputs.
Central differences of that closed form provide the independent uncertainty reference.

The engine fixture copies `project` and `expected.json` from edi's
`docs/user/cli/pd-neut-tof_ncaf-wish-5bank_start-fullprof` at `7ed17b57213c4c8fbb1595a94b55794c64ec5fce`.
Only the project description changes the old fit verb to “fit”; the numeric inputs are unchanged.
That case's PROVENANCE identifies FullProf 8.40's converged five-bank input and saved run. The generator copies the
measured observations into two points for the small gate and twenty for the nightly gate, each with five banks.
Only `kind: reference` atomic values from that file are correctness references. Engine regression pins in the same
file are retained for source fidelity and are not read by these gates. FullProf never runs in a test.

The standalone cross-bank witness has one structural cell, two scales and one width shared by an equality: four
independents. Its covariance reference is `(J.T J)^-1 * chi_square/(N-4)`, with J from central differences of the
calculation and the follower recomputed for every perturbation. It tests the single-structure powder path.

Scale is measured separately on the producer-to-view path; these fixtures impose no timing assertions.
