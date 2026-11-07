# Linked scan source references

Scan sources may live in any directory. On a shared volume, Save As writes a
relative reference that still resolves to the same physical source. A symlink
that reaches an outside input directory is therefore allowed. Missing linked
inputs preserve project opening and the declared scan; fitting reports the
missing source. Output and archive-member boundaries retain their existing gates.

The reference inputs are the committed CoSiO three-frame dataset bytes. The tests
compare those bytes before and after loading, fitting or saving, resolve saved
references against the new project directory, and match the fitted input names
to the independent directory inventory. The symlink target includes spaces and the save target is at a different depth,
so physical path resolution and rebasing are exercised away from an identity point.

| Previous witness | Current witness | Before | After |
| --- | --- | --- | --- |
| `test_edi_data_dir_lexical_escape_refuses_at_load` | `test_edi_external_data_dir_loads_and_roundtrips` | Absolute and parent-relative sources raise on load | Both load, rebase on Save As and reopen without changing input bytes |
| `test_edi_data_dir_symlink_escape_refuses_before_conversion_or_save` | `test_edi_external_symlink_data_dir_allows_fit_and_save` | An outside symlink raises on fit/save | Fit consumes every external dataset; Save As preserves its physical source; both preserve external bytes |

The frozen cadence inputs remain unchanged. Their old identities map one-to-one
to the replacement witnesses. New missing-source controls exercise both absolute
and parent-relative declarations. The GUI's data-not-found marker and Locate
folder action are covered separately from these core reader/writer checks.
