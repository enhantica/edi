"""Live controls for the current scan header and scene-graph projection consumers."""

import pytest

from tests.integration.py import test_scan_extended_contract as contract
from tests.integration.py.test_scan_app_contract import item, property_value, source


@pytest.mark.parametrize('channel', ['model', 'labels', 'table'])
def test_header_observer_rejects_disconnected_model_and_displayed_labels(monkeypatch, channel):
    path = 'qml/Pages/Experiment/ExperimentsGroup.qml'
    good = source(path)
    contract.test_scan_explorer_header_has_declared_columns_in_order()
    old, new = {
        'model': ('model: group.scanColumns', 'model: []'),
        'labels': ('text: column.modelData', 'text: "unused"'),
        'table': ('model: group.project ? group.project.experiments : null', 'model: null'),
    }[channel]
    changed = good.replace(old, new)
    assert changed != good, (
        'Dataset list wiring: each escape reaches the current displayed header or table'
    )
    monkeypatch.setattr(contract, 'source', lambda name: changed if name == path else source(name))
    with pytest.raises(AssertionError):
        contract.test_scan_explorer_header_has_declared_columns_in_order()


@pytest.mark.parametrize('channel', ['target', 'layer', 'coordinates', 'selection', 'low', 'high'])
def test_scene_graph_observer_rejects_disconnected_layer_hit_and_uncertainty(monkeypatch, channel):
    good = contract.evolution_component()
    contract.assert_evolution_bindings(good)
    if channel in {'low', 'high'}:
        path = 'src/evolution_view_model.cpp'
        native = source(path)
        old = 'point.y - point.error' if channel == 'low' else 'point.y + point.error'
        changed = native.replace(old, 'point.y')
        assert changed != native, (
            'Evolution wiring: the uncertainty escape reaches the actual drawing operation'
        )
        monkeypatch.setattr(
            contract, 'source', lambda name: changed if name == path else source(name)
        )
        with pytest.raises(AssertionError):
            contract.assert_evolution_bindings(good)
        return
    old, new = {
        'target': ('target: chart.evolution', 'target: unrelated.evolution'),
        'layer': ('value: chart.shown ? layer : null', 'value: null'),
        'coordinates': ('axisY.max - mouse.y / height', 'axisY.min + mouse.y / height'),
        'selection': ('currentExperimentIndex = dataset', 'currentExperimentIndex = 0'),
    }[channel]
    changed = good.replace(old, new)
    assert changed != good, (
        'Evolution wiring: each escape reaches the actual rendered layer or point event'
    )
    with pytest.raises(AssertionError):
        contract.assert_evolution_bindings(changed)


@pytest.mark.parametrize('consumer', ['chart', 'status'])
def test_actual_stale_markers_reject_constant_or_other_result_state(consumer):
    good = (
        contract.evolution_component()
        if consumer == 'chart'
        else item(source('qml/Components/StatusBar.qml'), 'statusBar.fit')
    )
    contract.assert_stale_marker(good)
    marker = item(
        good, 'evolution.outOfDate' if consumer == 'chart' else 'statusBar.fit.outOfDate'
    )
    visible = property_value(marker, 'visible')
    for wrong in (
        'true',
        'false',
        visible.replace('chart.evolution', 'other.evolution').replace('bar.fit', 'other.fit'),
    ):
        changed = good.replace(marker, marker.replace(visible, wrong))
        assert changed != good, (
            'Stale-result wiring: the escape changes the current retained-results marker'
        )
        with pytest.raises(AssertionError):
            contract.assert_stale_marker(changed)
