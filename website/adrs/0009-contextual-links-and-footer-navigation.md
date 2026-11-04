# ADR-0009: Contextual links and native footer navigation

Date: 2026-10-30
Status: accepted

## Prior art and decision

Pages accumulated Related Physics headings, related-documentation link trails, interface lists and hand-written Continue links. Native Zensical footer navigation was not enabled.

Enable `navigation.footer` in the selected documentation configuration. Previous/Next follows the existing navigation order and uses the native accessible presentation. The custom landing page retains its existing footer-free composition.

Remove generic Related Physics and related-documentation trails. Link scientific terms at the explanation or action where the reader needs them. Keep useful interface handoffs, compactly in context; do not remove citations, parameter-reference links, prerequisite links or purposeful tutorial next steps. Native Previous/Next replaces routine hand-written sequential links. Avoid a catch-all list merely because related pages exist.

## Validation

Strict builds verify all internal links and anchors. Check native Previous/Next targets and keyboard links at desktop/phone widths, ensure the landing page remains uncluttered, and inspect the Parameters page cited by the owner.


## Footer credit strip — 2026-11-04

Hide only the credit strip containing EasyDiffraction, Contributor documentation
and the Zensical generator credit. The selector is `.md-footer-meta`, not the whole
footer. Keep `navigation.footer` and the native Previous/Next links on documentation
pages. Home retains its existing empty footer override. The shared main template
inherits the ordinary footer. No page navigation or inline attribution is removed.

A strict site build checks valid links. Inspect generated Previous/Next anchors
on ordinary pages and the narrowly scoped credit-strip rule; Home remains free
of footer navigation. This replaces the earlier whole-footer suppression.
