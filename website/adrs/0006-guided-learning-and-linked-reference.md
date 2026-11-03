# ADR-0006: Guided learning and linked reference

Date: 2026-10-30
Status: accepted

Extend the existing generated GUI walkthrough, executed interface examples and scientific catalogue. Keep Y₂O₃/SPODI as the shared first refinement. Each action must have an observable checkpoint; finish by saving the project and offer a small optional exercise. Retain actual executed outputs and their existing capture provenance instead of inventing expected results.

Use one compact linked workflow diagram and a symptom/check/topic table where they reduce reading. Keep deep scientific explanations in Physics. Native screenshot selectors and descriptions retain the existing above-image tabs and fullscreen viewer.

Experiment badges and the parameter reference will extend the native dictionary and example metadata rather than the older library's vocabulary. Tags distinguish purpose, fitting mode and experiment axes; colour supplements their text. Every category and field gets a stable description link suitable for native context help.

The project's documentation architecture decision governs the site. Native callouts retain Zensical's defaults: visible notes for saving differences, warnings for loss of browser data, tips and expandable optional help.

The reference generator exports all native dictionary categories/items, CIF aliases, variants and options. Python paths are traversed against actual bound example objects and the committed category census; unknown mappings are visibly absent. GUI icon prefix rules are imported from ParameterNames.qml. Scientific role/equation links from the existing catalogue are retained. Every deep link is checked against a generated heading.

The first Application tutorial starts from standard CIF and XYE files: create the measurement, select its type, enter the wavelength/profile, exclude unwanted intervals and estimate the background. Fit scale/cell first, profile/calibration next, then background/independent coordinates. Keep displacement parameters fixed for the beginner fit and link their advanced treatment. Explicit Analysis setup captures may precede fitting; result captures and all Report captures still require a completed fit and closed popup. Calculate the before/after figures from the actual saved GUI checkpoints; keep the prepared Python/CLI route and its outputs separate.

2026-10-31 clarification: the Concept page reuses the earlier guide's instrument, detector, reduced pattern, refinement and crystal-model illustrations, retaining source URLs, hashes and credits in `assets/concepts/provenance.json`. Connect Acquisition → Reduction → Analysis with a responsive, icon-based diagram and native content tabs. A second diagram connects the sample/experiment model to calculation and comparison. Follow the two NOBUGS decks' compact pipeline/phase icons, without bringing presentation animation, facility software logos or slide furniture into user docs. Explain least squares versus Bayesian sampling while keeping older-library sampler availability separate from the current application. Figure descriptions remain above and left aligned; expand credits as optional supporting detail.

2026-11-01 owner revision: present Acquisition, Reduction and Analysis as consecutive illustrated sections in normal page flow. Keep the compact overview diagram and existing section anchors; all stage explanations and images remain visible without selecting tabs. This replaces the phase tabs chosen above.
