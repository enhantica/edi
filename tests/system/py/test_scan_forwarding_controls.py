"""Execute the real native forwarding boundaries and their original escape vectors."""

import pytest

from tests.integration.py import test_scan_app_contract as contract


def test_forwarding_controls_reject_wrong_selected_index_token_range_and_visibility(monkeypatch):
    original = contract.source
    # Load-data availability escapes live in test_plain_data_picker, with their
    # own valid controls for unloaded, loaded and imported rows.
    checks = [
        (
            'src/project_view_model.cpp',
            'setCurrentExperimentIndex(static_cast<int>(experiment_models_.size()) - 1);',
            'setCurrentExperimentIndex(0);',
            contract.test_create_experiment_is_enabled_and_routes_to_view_model,
            (),
        ),
        (
            'qml/Components/SelectorField.qml',
            'ApplicationInfo.activateSelector(index,',
            'ApplicationInfo.activateSelector(0,',
            contract.test_data_free_experiment_type_has_a_write_boundary,
            ('beamMode',),
        ),
        (
            'qml/Pages/Experiment/ExperimentTypeGroup.qml',
            'ApplicationInfo.chooseExperimentType(axis, token);',
            'row.project.setExperimentType(0, axis, token);',
            contract.test_data_free_experiment_type_has_a_write_boundary,
            ('beamMode',),
        ),
        (
            'qml/Pages/Experiment/ExperimentTypeGroup.qml',
            'row.experiment.polarisationOptions',
            'row.experiment.dimensionalityOptions',
            contract.test_disabled_placeholders_and_load_data_are_present,
            (),
        ),
        (
            'qml/Pages/Experiment/MeasuredRangeGroup.qml',
            'setRange(Number(text), group.range.maximum, group.range.step)',
            'setRange(group.range.minimum, Number(text), group.range.step)',
            contract.test_simulation_range_fields_have_live_write_bindings,
            ('minimum',),
        ),
        (
            'qml/Pages/Experiment/ExperimentsGroup.qml',
            'fileMode: FileDialog.OpenFiles',
            'fileMode: FileDialog.OpenFile',
            contract.test_create_experiment_is_enabled_and_routes_to_view_model,
            (),
        ),
        (
            'qml/Pages/Experiment/ExperimentsGroup.qml',
            'ApplicationInfo.formFilesOpened(request, files, true);',
            'group.project.loadExperiments([]);',
            contract.test_create_experiment_is_enabled_and_routes_to_view_model,
            (),
        ),
    ]
    for path, old, new, check, args in checks:
        changed = original(path).replace(old, new)
        assert changed != original(path), (
            'Scan wiring: every forwarding escape must reach its actual operation'
        )
        monkeypatch.setattr(
            contract,
            'source',
            lambda name, changed=changed, path=path: changed if name == path else original(name),
        )
        with pytest.raises((AssertionError, pytest.fail.Exception)):
            check(*args)
    monkeypatch.setattr(contract, 'source', original)
