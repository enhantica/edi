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


@pytest.mark.parametrize(
    ('case', 'control', 'profile', 'setting'),
    [
        (
            'pd-neut-cwl_lab6-echidna_fcj-asymmetry',
            'ECH0030684_LaB6_1p622A_fcj',
            'ECH0030684_LaB6_1p622A_fcj',
            '_peak.fullprof_fcj_limit 180',
        ),
        (
            'pd-neut-xray-cwl_pbso4-d1a-lab',
            'fixed',
            'fixed_1',
            '_peak.beba_evaluation pattern-point',
        ),
    ],
)
def test_imported_asymmetry_matches_fullprof_after_native_save(case, control, profile, setting, tmp_path):
    import math

    from edi import Project

    source = REFERENCES / case
    reference = {}
    rows = (source / f'{profile}.prf').read_text().split('BEGIN\n', 1)[1]
    for line in rows.splitlines():
        columns = line.split()
        if len(columns) != 4:
            break
        angle, _, intensity, _ = map(float, columns)
        reference[round(angle, 3)] = intensity

    def compare(project):
        project.calculate()
        data = next(iter(project.experiments)).data
        values = {
            round(x, 3): y for x, y in zip(data.axis(), data.intensity_calc, strict=True)
            if math.isfinite(y)
        }
        angles = reference.keys() & values.keys()
        assert len(angles) > .95 * len(values)
        squared_error = sum((values[x] - reference[x]) ** 2 for x in angles)
        assert squared_error / sum(reference[x] ** 2 for x in angles) < .01**2

    imported = Project.load(source / f'{control}.pcr')
    compare(imported)
    destination = tmp_path / 'native'
    imported.save_as(destination)
    assert any(setting in experiment.read_text() for experiment in (destination / 'experiments').glob('*.edi'))
    compare(Project.load(destination))
    exported = export_fixed(destination, tmp_path / 'fullprof')
    assert any('AsyLim' in row for row in exported)


@pytest.mark.parametrize('case', ['c15_t2_polarization/lif_single_polarized',
                                  'xray_doublet/absorption/lif_single_absorption'])
def test_imported_single_wavelength_xray_project_can_save(case, tmp_path):
    from edi import Project

    fixture = ROOT / 'tests/fixtures' / f'{case}.pcr'
    source = tmp_path / fixture.name
    rows = fixture.read_text().splitlines()
    rows[0] = 'COMM data_lif_scan'
    heading = next(i for i, line in enumerate(rows) if 'Data for PHASE number' in line)
    title = next(i for i in range(heading + 1, len(rows))
                 if rows[i].strip() and not rows[i].lstrip().startswith('!'))
    rows[title] = 'LiF.source'
    source.write_text('\n'.join(rows) + '\n')
    copyfile(fixture.with_suffix('.dat'), source.with_suffix('.dat'))

    project = Project.load(source)
    destination = tmp_path / 'native'
    project.save_as(destination)
    assert (destination / 'structures' / 'LiF_source.edi').is_file()
    assert '"data_lif_scan"' in (destination / 'project.edi').read_text()
    exported = export_fixed(destination, tmp_path / 'fullprof')
    index = next(i for i, line in enumerate(exported) if 'Lambda1 Lambda2 Ratio' in line)
    first, second, ratio = map(float, exported[index + 1].split()[:3])
    assert first == second
    assert ratio == 0
