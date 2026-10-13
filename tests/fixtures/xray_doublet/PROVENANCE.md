# Independent X-ray references

`generate.py` reads committed external files only. It does not import either product.
`manifest.json` records revisions and byte digests. The LiF `.prf`, `.sum`, `.pcr`,
`.dat` and `.bac` files are the original FullProf results distributed by
[diffraction-lib](https://github.com/easyscience/diffraction-lib/tree/0d9f10e412a0cd08d4dd0af95845dd9bb597dcdf/docs/docs/verification/fullprof/pd-xray-cwl_lif).
The profile is column 3 between BEGIN and END in each `.prf`. The authored
model carries the FullProf scale 0.01 directly. The polarized LiF example
uses a different normalization; that factor of two does not apply here.

The ionic coefficient references are Waasmaier & Kirfel, Acta Cryst. A51 (1995),
416–431, [DOI](https://doi.org/10.1107/S0108767394013292), from DABAX as distributed
by periodictable, and International Tables for Crystallography C (1992),
Table 6.1.1.4, pp. 500–502, from cctbx's independent transcription. The O2- entry
in that transcription cites Hovestreydt, Acta Cryst. A39 (1983), 268–269.
`published-f0.json` preserves all coefficients, including ions; evaluation uses
the published sum of Gaussians at sin(theta)/lambda, in inverse Angstroms.

Weight fractions use [Hill & Howard (1987)](https://doi.org/10.1107/S0021889887086199):
`w_p = S_p Z_p M_p V_p / sum(S Z M V)`. The authored phases contain the same
element, so its atomic mass cancels. Occupancies and atom counts independently
set the ratio of cell masses; unequal cell volumes and scales prevent a scale-only
normalisation from passing. Independent scale uncertainties propagate through
the analytic derivatives of this quotient.

To reproduce: `python generate.py /path/to/diffraction-lib /path/to/libraries`.

The new public instrument members follow `setup_wavelength`:
`setup_wavelength_2` and `setup_wavelength_2_to_1_ratio`, with matching
`_instrument` tokens. The ratio participates in the existing free-parameter walk.
The derived phase result uses `_linked_structure.weight_fraction` and a
`weight_fraction` member carrying `value` and `uncertainty`, beside `scale`.
The application displays it read-only. These names make the cross-repo seam
reviewable before implementation.

The PbSO4 round-robin files come from the same diffraction-lib revision,
`docs/docs/verification/fullprof/pd-xray-cwl_pbso4_round-robin/pbsox.*`.
FullProf's Npr 7 + BeBa shape has no exact map to the supported Caglioti
pseudo-Voigt + BeBa. The executable page fits widths, mixing and the four
coefficients from the issue-166 start and labels its bounds as regression
pins. Its file is added, but it does not count toward diffraction-lib parity.
Only the two LiF additions move that counter.

Fit anchoring uses Bragg's law, `2 theta = 2 asin(lambda / (2 d))`.
Jointly dilating a cell and its free wavelength leaves that line's positions
unchanged. A participating fixed positive second wavelength instead has
`d(2 theta)/d d = -lambda / (d^2 sqrt(1 - (lambda/(2 d))^2))`, which is nonzero.
The authored graph table therefore admits exactly components connected to an
active fixed second line; unrelated components, disabled bridges and inactive
banks carry no anchor. Both free wavelengths retain the dilation null direction.
The two wavelengths and nonzero ratio are authored inputs, never fit output.

The correlated Hill-Howard witness uses the same independently specified masses,
volumes and free scales, with stored coefficients `rho = 0.625` and `rho = -0.375`.
For `q_i = Z_i M_i V_i` and `D = S_0 q_0 + S_1 q_1`, the first fraction has
`g_0 = q_0 q_1 S_1 / D^2`, `g_1 = -q_0 q_1 S_0 / D^2` and
`variance = g_0^2 sigma_0^2 + g_1^2 sigma_1^2 + 2 g_0 g_1 rho sigma_0 sigma_1`.
The second fraction has the negative gradient and the same variance. The signed
cross term is checked in memory and after saving and reopening the stored loop;
no engine covariance or fit output supplies the expected value.

Relation-aware admission uses the same Bragg law and independently authored
relation derivatives. For `a(t)=a*t`, the angular response is
`d(2 theta)/dt = (d lambda/dt - lambda)/(a*sqrt(1-(lambda/(2*a))^2))` at `t=1`.
`line2=1.05*line1` has derivative 1.05; its reciprocal has derivative 1/1.05.
Both participating wavelengths therefore co-dilate with the free master and
have zero Bragg response, even though a dependent target has a nonfree flag.
Constant wavelengths and wavelengths following the fixed atom ADP have zero
wavelength response and a nonzero Bragg response; they remain genuine anchors.
The fixed ADP is independently declared zero and fixed in the existing input.

The ratio references use enabled constant values 0.375 and 0, and a disabled
constant relation. Effective participation comes from that declaration, not
from a prior stored ratio. Cold admission is checked before calculation,
then again after calculation and after save/reopen. The complete original
ordinary fixed/free/inactive/foreign-component matrix remains unchanged.
The symbolic cases include single, shared-structure and connected multiphase
models, with the anchor in the other bank and reversed bank ordering.
