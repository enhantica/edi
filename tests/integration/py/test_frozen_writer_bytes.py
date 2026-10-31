"""Real project load/save byte witnesses belong to the integration boundary.

The original byte pins and all assertions remain in their retained helpers.
Native serialization, input archive extraction and filesystem work are exercised
here under the integration runtime bound; the unit limit remains unchanged.
"""

import json
import os
import shutil
from types import SimpleNamespace

import pytest

from tests.fixtures.project_archive.recalculated_copy import check_geometry
from tests.fixtures.project_save.computed_columns import check as check_computed
from tests.fixtures.weight_fractions.single_phase_bytes import COLUMN
from tests.unit.py import test_c11_t4_cw_selection as cw
from tests.unit.py import test_c11_t56_project_identity as identity


def comparison_escapes(require, module, tmp_path, monkeypatch):
    original = module.historical_single_fraction
    control = tmp_path / 'control'
    saved = [control / 'saved'] if module is identity else sorted(control.glob('tof-*'))
    for damage in ['missing', 'wrong', 'other-byte']:
        reached = []

        def changed(name, data, damage=damage, reached=reached):
            if name.startswith('experiments/') and COLUMN in data:
                reached.append(name)
                header, rows = data.split(COLUMN, 1)
                first, rest = rows.split(b'\n', 1)
                old, value = first.rsplit(b' ', 1)
                assert value == b'1.0', 'The real saved comparison must reach a sole enabled link'
                if damage == 'missing':
                    data = header + rows
                elif damage == 'other-byte':
                    data += b'\n# unexpected experiment bytes\n'
                else:
                    data = header + COLUMN + old + b' 0.9\n' + rest
            return original(name, data)

        outputs = iter(saved)

        def replay(_source, outputs=outputs):
            output = next(outputs)
            return SimpleNamespace(
                save_as=lambda destination: shutil.copytree(
                    output, destination, copy_function=os.link
                ),
                metadata=SimpleNamespace(),
            )

        def stage(_destination):
            source = control / 'source'
            shutil.copy2(control / 'saved/project.edi', source / 'project.edi')
            return source

        with monkeypatch.context() as patch:
            patch.setattr(module, 'edi', SimpleNamespace(Project=SimpleNamespace(load=replay)))
            if module is identity:
                patch.setattr(module, '_stage_committed_corpus_project', stage)
            patch.setattr(module, 'historical_single_fraction', changed)
            with pytest.raises(AssertionError):
                require(tmp_path / damage)
        assert reached, 'Each escape must reach the real saved-experiment byte comparison'


def test_c11_t4_existing_tof_writer_goldens_remain_byte_exact(
    tmp_path, monkeypatch, record_property
):
    record_property('weight_fraction_before', 'absent column in immutable TOF golden trees')
    record_property(
        'weight_fraction_after', 'checked unity column; every other path and byte retained'
    )
    cw.require_existing_tof_writer_goldens(tmp_path / 'control')
    comparison_escapes(cw.require_existing_tof_writer_goldens, cw, tmp_path, monkeypatch)


def test_c11_t56_datablock_bytes_match_pre_fix_regression_pins(
    tmp_path, monkeypatch, record_property
):
    record_property('weight_fraction_before', 'absent column in immutable datablock hashes')
    record_property('weight_fraction_after', 'checked unity column; original hashes retained')
    identity.require_datablock_regression_pins(tmp_path / 'control')
    saved = tmp_path / 'control/saved'
    record_property('carried_computed_columns', json.dumps(check_computed(saved, identity.edi)))
    check_geometry((saved / 'structures/si.edi').read_bytes())
    comparison_escapes(identity.require_datablock_regression_pins, identity, tmp_path, monkeypatch)
