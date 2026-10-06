# profile contract hidden-contract adaptations

Authority: the committed owner amendment `ed78836d1`, the committed 2026-10-05 owner amendment,
and ADR-0080. All numerical tolerances and pre-rename numerical
pins remain unchanged. Changes below alter the selected model or the
serialization spelling explicitly; they do not bless current engine output.

| Contract                                                                       | Before                                                                              | After                                                                                                                                                                                                                                                 |
| ------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Existing CW numerical, cell, absorption, target/alias, scattering and AD gates | Generic pseudo-Voigt token/class selected TCH; the old FCJ name selected TCH + FCJ. | Canonical TCH and TCH + FCJ tokens/classes, with the same X/Y values, comparisons and bounds.                                                                                                                                                         |
| Python surface receipts and behavior witnesses                                 | Old TCH, FCJ and TCH + BeBa classes and members.                                    | Renamed TCH/FCJ classes; Npr5 BeBa exposes eta intercept/slope instead of TCH X/Y.                                                                                                                                                                    |
| profile contract and dictionary model matrices                                 | Shared TCH width rows for all CW shapes.                                            | Each declared shape carries its own slots. Npr5 BeBa uses mixing rows; TCH retains X/Y. The complete dictionary walk also reaches Gaussian, Lorentzian and Npr5.                                                                                      |
| Retired-token refusal                                                          | Required the prose word “unknown”.                                                  | Exact structured bad-enum diagnostic and the refused token.                                                                                                                                                                                           |
| Project CLI calculation                                                        | Expected calculated intensity in the measured-data category.                        | Reads the unchanged `_data_calc.intensity_calc` write-back contract.                                                                                                                                                                                  |
| Frozen historical serialization and external input receipts                    | Hashes over original TCH selector bytes.                                            | `historical.py` translates only exact selector tags; original hashes and numerical/model bytes remain authoritative. A changed width remains visible; Npr5 is never translated. Frozen archived subjects are staged under the canonical TCH spelling. |
| TCH rename regression bytes                                                    | Baseline TCH/FCJ native calculation bytes.                                          | The same byte pins on renamed models, with identical physical coefficients. Historical generators retain their original engine spelling through string composition.                                                                                   |
| New multiphase inventory                                                       | BEER's earlier scale-only vehicle; YAP inactive.                                    | BEER's owner FullProf full model and active YAP reference are covered; independent counts come from those committed projects. YAP adds a serialization fixed-point witness.                                                                           |

| YAP gate 6 | Every non-asymmetry fitted value compared while asymmetry was free. | All 52 independent fitted values compared against `asymmetry-off.sum` with four asymmetry coefficients fixed at zero in a fresh project. A separate full-model fit retains the 56-parameter and Rwp-within-5-percent checks against the original FullProf 4.08 percent. Each input/output SHA-256 is checked against FullProf provenance. |
| YAP control and visible generator | Old combined profile with TCH X/Y; loose eta attribute discovery. | Npr5 + BeBa with the dictionary's `mixing_eta_0/1`; physical occupancies, nonzero absorption, asymmetry limit, exclusions and background remain. |
| Fit admission | YAP gate lacked a corpus fit-site row. | Gate names the active `yap-spodi-3k` corpus case; tests use disposable copies. |
| Verification page contracts | Historical cryspy combination and three added page filenames; YAP wording heuristic. | PbSO4 names Npr5, the model change and FullProf convention difference; YAP page joins the inventory and names external origin and inexact-asymmetry fallback. |
| PbSO4 historical saved-byte subject | Frozen TCH + BeBa model. | Replaced Npr5 project receives a typed-model and second-save fixed-point check; its immutable old receipt is retained as history. |
| Third-party enum oracle | Raw historical CW selector spellings mixed with active enums. | All six owner selectors in the active map; unchanged original upstream enum evidence retained as base64 JSON by the visible generator. Other upstream evidence is untouched. |
| App fixture oracle | Removed profile spelling and TCH widths on BeBa. | Visible generator emits canonical profile and Npr5 mixing fields. Qt/screenshot execution remains off under the standing owner ruling. |
| Checked PbSO4 screenshot | Original image and independently observed X/Y labels. | Same image and observation retained. Producer's rewritten Eta0/Eta1 caption does not match the image; this remains a product documentation red. No new screenshot is manufactured. |

The asymmetry-off and full-model fits use separate copies of the delivered
starting project. FullProf expectations are parsed from committed authoring-time
outputs; neither tested engine creates a correctness expectation.

The profile contract survey now explicitly classifies the new Gaussian, Lorentzian and Npr5 class/member and enum routes as non-operation public rows. Existing route classifications and model-operation signature controls remain. Crysta's narrow unit surface witnesses cover their declared descriptors, distinct enums and foreign-slot absence; runtime-attributed evidence is appended by the visible generator, without changing either coverage floor.

The corresponding edi survey also lacked profile contract's LinkedStructures container and its collection operations. Those explicit routes now receive the same other-public classification as the existing structure and experiment collections; no model-operation signature route is removed.

The complete verification adds explicit remaining adaptations: profile contract original
calculation inputs are hash-checked before exact selector translation; scan and
unconstrained saved-byte witnesses reverse only that selector, retaining every
original hash and numerical pin. Condition-free YAP transport must use `--dry`;
declared overrides still require disposable copies, and removing `--dry` reaches
the actual read-only predicate. Both compiler census oracles give the requested
subject header precedence over SDK dependencies; same-named SDK header escapes
exercise that boundary for public and private members.

The frozen pre-task Python surface is restored byte for byte from `d4e0ebf^`
(SHA256 `7afbb58d7c01d0a9e2193a17611b62f77ad8dcf28df1ec08fa5528f43851101e`).
Only its TCH/FCJ class-owner paths are translated after that digest check; the
baseline cannot shrink, grow or take current runtime output as its reference.

YAP joins the complete verification-source and stripped-notebook inventory. Its
named SPODI bank and included FullProf reference alias receive the same candidate
and reference provenance checks as the earlier pages, with oracle substitution,
candidate substitution and foreign-bank escapes. BEER's page now fits observations
on the owner FullProf model; the old Bragg-pattern substitution vehicle moves to
YAP. BEER's independent fitted-value and Rwp gates remain.

profile contract makes unlinking a precondition of structure removal. Lifecycle and warmed
relation vehicles unlink first, retaining all attachment, dependence, free-write
and closed-form geometry assertions. Residual failures in those assertions are
product findings, not exemptions. Corpus and binary observers use the proved
comparison source and selected build environment instead of absent ordinary-pin
paths; prepared invalid-input corpus copies remain supported.

The removed TCH + BeBa page's historical closeness bounds remain in
`c14_t4_neutron/page_pins.json`; that subject is retired under ADR-0080. The new
Npr5 page executes its own labelled regression comparisons and is checked for its
typed shape and mixing slots, alongside the independently gated asymmetry family
and disabled-asymmetry escape. Every retained-model page keeps its original bounds.
The STAR loop inventory keeps all original table metadata and digests. Exact token
translation covers the rename; only the replacement PbSO4 model gets an explicitly
labelled new structural input receipt via `e04_t2/generate.py`, retaining the old
digest in the same receipt. No numerical correctness value is generated there.

The native scene observer also selects that same reference phase for each site label.
The adapter conversion vehicle replaces its default placeholder link with the one
intended probe link before checking every original conversion value. The generated
large-geometry reference relinks its retained banks to the explicitly generated
structure after replacement; all independent requested-state bits, fifty samples
and five warmups remain unchanged.

The absorption-cache reference keeps the source structure's explicit identity,
so its converted experiment still links that independent structure. All original
parameter values, cache-stamp predicates and pattern-change bounds stay fixed.
