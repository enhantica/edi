"""Exercise each retained scan, recipe, loop and numeric-input witness through its caller."""

import itertools
import shutil
from pathlib import Path

import pytest

from tests.fixtures.multiphase import support
from tests.fixtures.table_display import metadata_bytes
from tests.integration.py import test_c11_t62_vendored_scan as scan
from tests.integration.py import test_e04_t2_build_contract as loops
from tests.system.py import test_e04_t11_wasm_delivery as native

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize('channel', ['scan', 'agreement', 'loops', 'native'])
@pytest.mark.parametrize('damage', ['descriptor', 'science', 'data', 'inventory'])
def test_catalogue_projection_refuses_every_retained_input_escape(
    tmp_path, monkeypatch, channel, damage
):
    case = {
        'scan': 'pd-neut-cwl_cosio-d20_scan-324f',
        'agreement': 'pd-neut-cwl_yap-spodi_3k',
        'loops': 'pd-neut-cwl_lab6-echidna_fcj-asymmetry',
        'native': 'pd-neut-cwl_lbco-hrpt_start-4',
    }[channel]
    relative = Path('docs/user/cli') / case / 'project'
    project = tmp_path / relative
    shutil.copytree(ROOT / relative, project)
    monkeypatch.setattr(metadata_bytes, 'ROOT', tmp_path)
    module = {'scan': scan, 'loops': loops, 'native': native}.get(channel)
    if module is not None:
        monkeypatch.setattr(module, 'ROOT', tmp_path)
    fixture_paths = {
        'scan': [
            'tests/fixtures/c11_t62/scan-inputs.json',
            'tests/fixtures/constraint_expressions/byte-pins.json',
            'tests/fixtures/e04_t12_public_release/saved-metadata.json',
            'tests/fixtures/e04_t12_public_release/project-metadata.json',
        ],
        'loops': [
            'tests/fixtures/e04_t2/loops.json',
            'tests/fixtures/e04_t2/generate.py',
            'tests/fixtures/e04_t2/replacement-input.json',
        ],
    }.get(channel, [])
    for name in fixture_paths:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, target)
    experiment = next((project / 'experiments').glob('*.edi'))
    counter = itertools.count()

    def observe():
        if channel == 'scan':
            scan.test_cli_scan_contains_the_original_inputs()
            scan.test_cli_full_scan_has_every_reversed_temperature_pair()
        elif channel == 'agreement':
            support.stage_delivered_corpus_project(
                project, 'yap-spodi-3k', tmp_path / ('staged-' + str(next(counter)))
            )
        elif channel == 'loops':
            loops.test_loop_expectations_cover_fixture_bytes(
                experiment.relative_to(tmp_path).as_posix()
            )
        else:
            native.test_native_fixture_is_bound_to_the_committed_nontrivial_project()

    observe()
    if damage == 'descriptor':
        target = project / 'project.edi' if channel in {'scan', 'native'} else experiment
        tag = '_metadata.title' if target.name == 'project.edi' else '_experiment_type.sample_form'
        with target.open('a') as stream:
            stream.write('\n' + tag + ' "wrong or duplicate"\n')
    elif damage == 'science':
        with experiment.open('a') as stream:
            stream.write('\n_peak.cutoff_fwhm 3.125\n')
    elif damage == 'data':
        target = next(project.rglob('*.dat'), experiment)
        with target.open('a') as stream:
            stream.write('\n12.5 31.76 0.75\n')
    elif channel == 'loops':
        with experiment.open('a') as stream:
            stream.write('\nloop_\n_unexpected.id\nextra\n')
    else:
        directory = {
            'scan': project / 'experiments/d20_scan',
            'agreement': project / 'structures',
            'native': project,
        }[channel]
        (directory / ('extra.dat' if channel == 'scan' else 'extra.edi')).write_text('extra\n')
    with pytest.raises(AssertionError):
        observe()
