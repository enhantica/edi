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

Executable checks now include single-crystal automatic scale initialization on
project load. The engine checks also compose user exclusion with body centring.
The edi QML checks exercise powder measured-data loading and one undo, hold the
authored linear background fixed, and inspect visible disabled Free controls and
the plain idle Fit icon in the production host. Their generated observations
exercise a linearity invariant; they are not an independent diffraction model.
A separate edi fit witness copies the pinned Tb2Ti2O7 corpus unchanged and uses
its independently computed FullProf normal-equation references. It does not
admit synthetic fit inputs or change the fit policy.

Still requiring a declared product contract: single-crystal range serialization,
merge/absence settings and result fields, the scatter estimator, reflection-table
toggle/undo and chart reasons. Neither current category census nor public Python
surface declares those features. The common-scale phase-add/remove trigger and
two-phase ratio gate also remain open. These are coverage gaps, not passing gates.

The following independent reference cases are ready for those adapters:
- Cubic cell a=6 A: d(100)=6, d(200)=3, d(211)=sqrt(6), d(220)=3/sqrt(2).
  sin(theta)/lambda is 1/(2d), independent of wavelength; use a non-unit
  wavelength (0.8 A) when testing a conversion from angle.
- P1 Friedel pairs (100)/(-100), (010)/(0-10): I=(10,14,25,40),
  sigma=(1,2,3,1). Weighted means are 10.8 and 38.5; propagated uncertainties
  sqrt(0.8) and sqrt(0.9). With weighted scatter of the mean defined as
  sqrt(sum(w*(I-mean)^2)/((n-1)*sum(w))), the scatter uncertainties are 1.6
  and 4.5. The packet does not yet define which scatter estimator it chooses.
  Rint numerator is 19; sum of unmerged intensities is 89. Source:
  International Tables F, section 21.1.7.1.1,
  https://onlinelibrary.wiley.com/iucr/itc/Fb/ch21o1v0001/sec21o1o7o1o1/
  SHELXTL manual defines R(sigma)=sum(sigma(F squared))/sum(F squared):
  https://xray.uky.edu/Resources/manuals/Shelxtl-manual.pdf
  The merged-value convention must be stated before an R-sigma adapter is gated.
- Fixed-background WLS: two phase profiles (1,2,0,3), (0,1,4,1), initial
  scales (2,3), background (5,7,11,13), observations (10,26,44,42),
  sigma (1,2,3,4). k=sum(w*(observed-background)*calculated)/sum(w*calculated^2),
  with calculated=(2,7,12,9). The same scalar problem applies to single
  crystal F squared. This is the normal equation, derived from differentiating
  the weighted sum of squared residuals; background is held fixed.
