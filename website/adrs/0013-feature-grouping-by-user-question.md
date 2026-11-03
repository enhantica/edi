# ADR-0013: Feature groups answer one user question

Date: 2026-10-30
Status: accepted — owner requests an audit of combined feature groups

The feature catalogue used compact mixed headings. Separate unrelated capabilities even when they share a broad workflow stage. Preserve every feature row and its per-interface status, keep planned/proposed rows beside related current work, and retain old combined anchors for incoming links.

| Prior group | Result and rationale |
| --- | --- |
| Absorption and preferred orientation | Separate physical corrections and GUI groups. |
| Background and excluded observations | Background models, background estimation and observation exclusions; modelling a baseline, proposing its values and admitting observations are different tasks. |
| Instrument and calibration | Calibration versus radiation settings; the reciprocal-TOF caveat stays with calibration. |
| Calculation and fitting modes | Forward calculation versus fitting modes. |
| Parameters and fit assessment | Refinement controls versus assessing results. |
| Project files and measured input | Complete-project persistence versus creating/importing model inputs. |
| Charts and reports | Visual inspection versus exporting reports. |

Retain coherent scientific families: crystal structure, atomic displacement, scattering models, diffraction modes, each profile family and single-crystal extinction. Their rows describe alternatives or parts of one recognisable model, not unrelated operations. A practical how-to may still coordinate several explicitly named steps; this decision concerns discoverable capability grouping rather than forbidding cross-category tutorials.

Validate that the feature row/status multiset is unchanged, all planned/proposed entries remain contextual, legacy/new anchors resolve and the feature tables remain readable on desktop and phone.

Header transformations must use line-bounded, unique matches. Compare the complete feature-row/status inventory with the committed prior version after every regrouping and before publication; a scoped section check alone is insufficient.

2026-10-31 clarification: separate Le Bail from Pawley and Sequential from Independent in capability rows, retaining the shared family headings and old group anchors. Model input explicitly lists structure and experiment `.edi` imports. Give the Structure viewer a dedicated capability table, with magnetic-moment arrows marked Planned. List correlation matrices, stacked datasets, intensity maps and parameter evolution individually; distinguish interactive workspace views from generated HTML report figures and raw result data. Availability was checked against edi `597812c0` (`lib/edi/__init__.py`, `app/qml/Components/StructureToolbar.qml`, `app/qml/Components/StructureView.qml`, `app/qml/Pages/Analysis/AnalysisPage.qml`, `data/report/report.js`).
