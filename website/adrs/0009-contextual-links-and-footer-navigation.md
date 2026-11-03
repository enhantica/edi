# ADR-0009: Contextual links and native footer navigation

Date: 2026-10-30
Status: accepted — owner requests less clutter and Previous/Next navigation

## Prior art and decision

Pages accumulated Related Physics headings, related-documentation link trails, interface lists and hand-written Continue links. Native Zensical footer navigation was not enabled.

Enable `navigation.footer` in the selected documentation configuration. Previous/Next follows the existing navigation order and uses the native accessible presentation. The custom landing page retains its existing footer-free composition.

Remove generic Related Physics and related-documentation trails. Link scientific terms at the explanation or action where the reader needs them. Keep useful interface handoffs, compactly in context; do not remove citations, parameter-reference links, prerequisite links or purposeful tutorial next steps. Native Previous/Next replaces routine hand-written sequential links. Avoid a catch-all list merely because related pages exist.

## Validation

Strict builds verify all internal links and anchors. Check native Previous/Next targets and keyboard links at desktop/phone widths, ensure the landing page remains uncluttered, and inspect the Parameters page cited by the owner.
