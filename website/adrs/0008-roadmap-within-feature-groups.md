# ADR-0008: Roadmap items within their scientific groups

Date: 2026-10-30
Status: accepted — owner requested contextual grouping

## Prior art and decision

Features and roadmap previously separated planned and proposed rows into a final Planned work section. The model catalogue sent unrelated future models to one shared paragraph. This obscured features when readers scanned by scientific role.

Place every existing planned or proposed item beside the related implemented features: Ikeda–Carpenter under TOF profiles; magnetic, polarized and total-scattering/PDF work under scattering; Le Bail / Pawley under calculation and fitting; single-crystal exclusions beside powder exclusions; fuller CIF input and PDF-report improvements beside input and reporting. Keep the existing per-interface statuses and preserve Proposed versus Planned. Planning does not establish interface delivery or a selectable model token.

Give planned scientific models contextual Physics anchors with short descriptions and visible status text. Retain the previous planned-scientific-models anchors for incoming links. Keep the executable machine-readable model registry unchanged. Existing capabilities retain their availability; improving PDF reports does not make current PDF output unavailable.

The project's documentation architecture decision owns the wider convention. This entry records the approved extension and the implementation beside its source.

## Validation

Strict build checks local links and anchors. Compare the moved feature rows and statuses with their prior version, then check desktop/phone rendering and accessible statuses in the actual feature tables.
