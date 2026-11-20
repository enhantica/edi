"""Exercise the FullProf export command with verified projects."""

import os
from pathlib import Path
from shutil import copyfile
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[3]
REFERENCES = ROOT / 'knowledge/verification/fullprof'


def export_fixed(source, destination):
    candidates = [
        os.environ.get('EDI_CLI_EXECUTABLE'),
        ROOT / 'build/ci-consumer/cli/easydiffraction',
        ROOT / 'build/ci/cli/easydiffraction',
    ]
    binary = next((Path(path) for path in candidates if path and Path(path).is_file()), None)
    assert binary is not None, 'FullProf export must be exercised through the built standalone command'
    result = subprocess.run(
        [str(binary), 'export-fullprof', str(source), str(destination), '--fixed'],
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    assert result.returncode == 0, result.stderr
    return (destination / 'project.pcr').read_text().splitlines()


@pytest.mark.parametrize(
    ('case', 'control', 'symbol'),
    [
        ('pd-xray-cwl_lif_single', 'lif_single_unpolarized', 'F m -3 m'),
        ('pd-neut-tof_diamond-dream_basic', 'diamond', 'F d -3 m:1'),
        ('pd-neut-tof_si-sepd', 'fixed', 'F d -3 m'),
    ],
)
def test_fullprof_export_space_group(case, control, symbol, tmp_path):
    source = REFERENCES / case / f'{control}.pcr'
    groups = [
        line.partition('<--Space group symbol')[0].strip()
        for line in export_fixed(source, tmp_path / 'fullprof')
        if '<--Space group symbol' in line
    ]
    assert groups == [symbol]


def test_fullprof_export_writes_background_and_exclusions_in_bank_order(tmp_path):
    reference = REFERENCES / 'pd-neut-tof_ncaf-wish'
    lines = (reference / 'fixed.pcr').read_text().splitlines()
    job = next(i for i, line in enumerate(lines) if line.startswith('!Job '))
    for i, line in enumerate(lines):
        if line.startswith('!Irf Npr Jtyp'):
            lines[i + 1] = ' '.join(lines[i + 1].split()[:3])
    positions = [i for i, line in enumerate(lines) if line.startswith('!2Theta/TOF/E(Kev)')]
    for bank, position in reversed(list(enumerate(positions, start=1))):
        row = lines[job + bank].split('!')[0].split()
        row[3] = '1'
        lines[job + bank] = ' '.join(row)
        last_point = position + int(row[2])
        lines[last_point + 1:last_point + 1] = [f'! Excluded regions for Pattern# {bank}', '1 2']
        data = f'fixed_{bank}.dat'
        copyfile(reference / data, tmp_path / data)
    source = tmp_path / 'fixed.pcr'
    source.write_text('\n'.join(lines) + '\n')

    headers = [line for line in export_fixed(source, tmp_path / 'fullprof')
               if line.startswith(('!2Theta/TOF/E(Kev)', '! Excluded regions'))]
    assert headers == [
        heading for bank in range(1, 6)
        for heading in (
            f'!2Theta/TOF/E(Kev) Background for Pattern# {bank}',
            f'! Excluded regions (LowT HighT) for Pattern# {bank}',
        )
    ]
