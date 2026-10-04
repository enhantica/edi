"""development hub  unit 11: independently count measured and explicitly unmeasured rows."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def test_inventory_writer_keeps_unmeasured_rows_and_rejects_a_hand_edited_header(tmp_path):
    root = Path(__file__).resolve().parents[3]
    spec = importlib.util.spec_from_file_location(
        'e09_t74_bank', root / 'tools/checks/per_pr_runtimes.py'
    )
    bank = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(bank)
    rows = {'tests/unit/py/test_a.py::test_one': 0.012, 'tests/unit/cpp/test_c.cpp::case': 0.019}
    holes = {'tests/unit/py/test_b.py::test_unmeasured': 'prescribed fixture hole'}
    text = bank.render_manifest(rows, [' independent fixture'], unmeasured=holes)
    for key, value in {'python': 2, 'cpp': 1, 'measured': 2, 'unmeasured': 1}.items():
        assert f'# inventory_{key} = {value}\n' in text, (
            ' unit 11: inventory counts include holes without manufacturing measurements'
        )
    assert (
        'UNMEASURED:prescribed fixture hole\ttests/unit/py/test_b.py::test_unmeasured' in text
    ), ' unit 11: the writer preserves each explicitly unmeasured identity and reason'
    manifest = tmp_path / 'runtimes.tsv'
    manifest.write_text(text)
    bank.load_manifest(manifest)
    manifest.write_text(text.replace('# inventory_measured = 2', '# inventory_measured = 3'))
    with pytest.raises(bank.ManifestError, match='inventory'):
        bank.load_manifest(manifest)
