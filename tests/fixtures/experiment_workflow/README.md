# Experiment workflow references

A new experiment always starts from Create experiment; measured data loads into
or replaces the selected one.

`replacement.xye` is hand authored: four distinct coordinates, intensities and
uncertainties. The retained LBCO CIF/experiment and FullProf TbTi reflection file
are independent inputs. A fresh experiment of the same type is the replacement
reference. Type and parameter preservation, unchanged rejected state and Undo are
roundtrip invariants, not values sampled from the implementation.

## Unfinished checkpoint

Testing was stopped at the previous checkpoint. These workflow gates are an unfinished
checkpoint, not completed acceptance evidence. No runs were started after that
instruction. Runtime banking, both passenger runtime audits and the final hub
requirement diagnostic remain pending; the runtime table is unchanged. Resume
those steps before claiming the new nodes are ready for CI.

Before parking, the scoped `test_experiment_create_and_replace.py` replay on
edi `1b14d72e` recorded 5 failures and 6 passes in
the retained scoped experiment replay log. Its independent reference
and preservation controls reached the ordinary loader. The failures concern the
create-first menu, retired type group and bottom web Load action. The complete
lesson walk exceeded the original host protocol timeout; the subsequent longer
timeout and shared-observation changes have not been replayed. That timeout is
not counted as a product failure. The overwrite gates have not been replayed.

Existing assertion adaptations, before and after:

- `OnlineLoadCase.check_actions_and_formats`: the measured-data section title
  was “Measured data into”; the owner record now requires “Load measured data
  into”, retaining the selected experiment's name and format checks.
- `OnlineLoadCase.check_new_target_import`: measured data previously created an
  experiment implicitly. It now first clicks Create experiment, then imports
  into that selected empty experiment. Undo first restores the empty experiment
  and then undoes its explicit creation. Refusal preserves the empty experiment
  and adds no import history. The file/web routes and original admission and
  measured-value checks remain.

The synthetic replacement is compared with a fresh same-type import. Neither
the replacement nor overwrite expectations come from production output. The
overwrite control compares with fresh creation in an empty folder; cancellation
and failure compare every original project byte. Tutorial completion uses real
Next actions, the independent HRPT data and written 1.494 angstrom setting,
followed by restoration of the original user project.

The following gates remain to be completed: journal formatting,
session search memory, count/chunk loading, linked structures and multi-dataset
coverage. Earlier completed work remains recorded separately.
