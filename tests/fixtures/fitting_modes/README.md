# Retained inactive-weight byte pins

The owner's 2026-10-11 fitting-mode decision removes the joint weights loop from
saved non-joint analyses. The original saved-byte JSON hashes remain immutable.
`historical_bytes.py` restores only that removed loop into the observed bytes,
using the committed input experiment identities and weights (default 1).
Every other byte and the complete file inventory still face the old hashes.
Active joint analyses are returned untouched. Non-joint observations carrying a
joint category, duplicate or unknown input rows, or an unexpected separator
refuse the projection. Closed-form controls use weights 0.625 and 2.125, retain
result bytes, and exercise unrelated byte damage. Second-save fixed-point
observations continue comparing raw current serialization.

The app's frozen single-mode Text expectation removes precisely the trailing
inactive loop from the expected reference, leaving actual Text unmodified.
