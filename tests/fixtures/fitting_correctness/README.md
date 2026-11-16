# Fitting correctness witnesses

The one-atom neutron model uses Sears (1992) Ni coherent scattering length
1.03 in 10^-12 cm, zero displacement, full occupancy and an orthogonal cell.
P1 gives F squared = 1.03 squared for every reflection. Body centring gives
zero when h+k+l is odd and four times that value otherwise, by adding the
origin and (1/2,1/2,1/2) amplitudes. The permitted and absent rows have unequal
weights; a weak negative permitted measurement remains part of the fit.

Sources:
- SHELXL instructions, OMIT h k l and LIST 4:
  https://shelx.uni-goettingen.de/shelxl_html.php
  An omitted reflection contributes no residual; exported status is x.
- IUCr reflection conditions (International Tables A, tables 2.1.3.5–7):
  https://dictionary.iucr.org/Reflection_conditions
- Sears neutron scattering lengths, Neutron News 3(3), 26–37 (1992).

Executable checks include single-crystal automatic scale initialization on
measured-data load; opening a saved project preserves its declared scale. The engine checks also compose user exclusion with body centring.
The edi QML checks exercise powder measured-data loading and one undo, hold the
authored linear background fixed, and inspect visible disabled Free controls and
the plain idle Fit icon in the production host. Their generated observations
exercise a linearity invariant; they are not an independent diffraction model.
A separate edi fit witness copies the pinned Tb2Ti2O7 corpus unchanged and uses
its independently computed FullProf normal-equation references. It does not
admit synthetic fit inputs or change the fit policy.

The admission adapters bind the declared file interfaces: `_excluded_reflection`,
`_excluded_region.axis`, `_reflns.merge` and `_reflns.absences`. They observe the
real native fit and saved computed categories, including original-row statuses,
counts and agreement factors. Opening a saved project preserves its scale;
automatic common-factor fitting belongs to measured-data and phase-link edits.

The following independent reference cases are ready for those adapters:
- Cubic cell a=6 A: d(100)=6, d(200)=3, d(211)=sqrt(6), d(220)=3/sqrt(2).
  sin(theta)/lambda is 1/(2d), independent of wavelength; use a non-unit
  wavelength (0.8 A) when testing a conversion from angle.
- P1 Friedel pairs (100)/(-100), (010)/(0-10): I=(10,14,25,40),
  sigma=(1,2,3,1). Weighted means are 10.8 and 38.5; propagated uncertainties
  sqrt(0.8) and sqrt(0.9). With weighted scatter of the mean defined as
  sqrt(sum(w*(I-mean)^2)/((n-1)*sum(w))), the scatter uncertainties are 1.6
  and 4.5. The selected product convention is the weighted scatter above (CCSL WTMEAN).
  Rint numerator is 19; sum of unmerged intensities is 89. Source:
  International Tables F, section 21.1.7.1.1,
  https://onlinelibrary.wiley.com/iucr/itc/Fb/ch21o1v0001/sec21o1o7o1o1/
  SHELXTL manual defines R(sigma)=sum(sigma(F squared))/sum(F squared):
  https://xray.uky.edu/Resources/manuals/Shelxtl-manual.pdf
  The executable R-sigma adapter uses the larger of weighted scatter and propagated uncertainty, over used merged rows.
- Fixed-background WLS: two phase profiles (1,2,0,3), (0,1,4,1), initial
  scales (2,3), background (5,7,11,13), observations (10,26,44,42),
  sigma (1,2,3,4). k=sum(w*(observed-background)*calculated)/sum(w*calculated^2),
  with calculated=(2,7,12,9). The same scalar problem applies to single
  crystal F squared. This is the normal equation, derived from differentiating
  the weighted sum of squared residuals; background is held fixed.

## Measured-list merge references

`generate_merge_references.py` reads only the frozen measured input rows of the
single-crystal fixture, never an engine calculation. It writes decimal weighted
means, propagated uncertainties, both scatter conventions, Rint over repeated
observations only, and R-sigma over the merged list. Negative intensities stay
signed. The source digest is recorded. Running the generator reproduces
`merge_reference.json` in either product.

The real Tb2Ti2O7 list has no repeated Laue equivalents. Its Rint is undefined;
it is not given a fabricated zero. The separately named Friedel duplicate
witness retains the first measured rows and adds opposite indices with authored
intensity offsets and unequal uncertainties. It is a constructed input, not an
additional measured dataset or an engine regression pin.

The original manual defines scatter using the rms deviation about the mean,
divided by sqrt(n-1). The weighted-scatter alternative is retained alongside it
for comparison. The executable adapter uses the CCSL weighted scatter, independently derived from WTMEAN; the JSON now records that merged uncertainty and its R-sigma too.

Sources: SHELX-97 manual section 2, original manual hosted at
https://ccc.bc.edu/content/dam/bc1/schools/mcas/Chemistry/pdf/research/xray/shelx-97.pdf;
International Tables F section 21.1.7.1.1 for Rmerge;
https://dictionary.iucr.org/Reflection_conditions for centring, glide and screw
conditions. The fixture space groups are P 21/c (b1) and F d -3 m. Their point
rotations give the explicit equivalent-index operations in the generator.

## Review-corrected reduced-index contract

SHELXL OMIT is applied to the final reduced index. With `none`, every repeated
measurement of that complete signed tuple is omitted. With `point_group`, all
proper point-group equivalents mapping to that index are omitted; with
`laue_class`, inversion is included too. Ranges and absences still have their
specified first-reason precedence. An omitted reduced group contributes neither
a merged intensity nor an agreement factor. This corrects the raw-index-first
policy rejected by review r8; no product deviation from SHELXL is retained.
Source: https://shelx.uni-goettingen.de/shelxl_html.php#OMIT.

`contracts.py` regenerates the orthorhombic 222/mmm orbit witnesses and the
body-centred Ni project plus `admission_reference.json`. The complete-tuple
controls share h but differ in k, l or signs. Proper 222 rotations change two
signs; inversion generates mmm. I centring requires even h+k+l. These are
independent crystallographic operations, not symmetry engine output.

The combined witness has raw rejected high intensities, unequal uncertainties,
nonproportional equivalents, a weak post-merge group and nonzero factors.
Its expected scales are closed-form inverse-variance normal equations after
all declared admission steps. For body-centred origin Ni the predictor is
F²(hkl)=(1.03)² [1+(-1)^(h+k+l)]²: 4*(1.03)² for allowed reflections and
exactly zero for a centring absence. When absences are included, their observed
intensities contribute to the residual and its observation count, but to neither
sum in the scale normal equation. This applies to every generated dataset,
including the point-group/include secondary dataset. Changing an included
absence's observed intensity cannot change the expected scale.
The powder engine profile is only an input stimulus to a linear normal-equation
invariant; no diffraction accuracy is inferred from it. Counterfactual controls
exercise the actual gate checkers with the review's wrong algorithms or output.
