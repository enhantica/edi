"""runtime banking uses the declared  module-cost convention.

Closed-form log inputs prove cost conservation through the actual focused writer.
No wall-clock timing or implementation-generated expectation is used here.
"""

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize('shared', [0.4, 8.0])
def test_focused_writer_separates_shared_cost_before_per_test_bound(shared, monkeypatch, tmp_path):
    spec = importlib.util.spec_from_file_location(
        'e04_t10_runtime_cost', ROOT / 'tools/checks/per_pr_runtimes.py'
    )
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    module = 'tests/system/py/test_shared_measurement.py'
    node = module + '::test_first_row'
    manifest = tmp_path / 'manifest.tsv'
    manifest.write_text(audit.render_manifest({}, ['Recorded from: prior.log']))
    monkeypatch.setattr(audit, 'MANIFEST', manifest)
    monkeypatch.setattr(audit, 'collect_nodeids', lambda: [node])
    log = tmp_path / 'durations.log'
    log.write_text(
        f'{shared:.2f}s setup {node}\n0.03s call {node}\n'
        '================ 1 passed ================\n'
    )
    costs = tmp_path / 'costs.json'
    costs.write_text(json.dumps({'module_costs': {module: shared}, 'completed': [node]}))
    assert audit.update(log, costs) == 0, (
        '/ shared setup is reconciled before the unchanged per-test bound'
    )
    _, rows = audit.load_manifest(manifest)
    assert rows[node] == pytest.approx(0.03, abs=0.0005), (
        '/ focused writer banks only the independently stated node cost'
    )
    assert audit.load_module_costs(manifest) == {module: shared}, (
        '/ the complete shared measurement cost remains explicitly recorded'
    )
