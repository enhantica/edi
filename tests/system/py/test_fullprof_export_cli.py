"""Exercise the FullProf export command with verified projects."""

import os
import subprocess
from pathlib import Path
from shutil import copyfile

import pytest
from edi import Project

ROOT = Path(__file__).resolve().parents[3]
REFERENCES = ROOT / 'knowledge/verification/fullprof'


def export_fixed(source, destination):
    candidates = [
        os.environ.get('EDI_CLI_EXECUTABLE'),
        ROOT / 'build/ci-consumer/cli/easydiffraction',
        ROOT / 'build/ci/cli/easydiffraction',
    ]
    binary = next((Path(path) for path in candidates if path and Path(path).is_file()), None)
    assert binary is not None, (
        'FullProf export must be exercised through the built standalone command'
    )
    result = subprocess.run(
        [str(binary), 'export-fullprof', str(source), str(destination), '--fixed'],
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    assert result.returncode == 0, (
        'FullProf export requires the built standalone command and a successful exit: '
        + result.stderr
    )
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
    assert groups == [symbol], (
        'FullProf export preserves the source space-group symbol and coordinate setting.'
    )


def test_fullprof_export_writes_background_and_exclusions_in_bank_order(tmp_path):
    reference = REFERENCES / 'pd-neut-tof_ncaf-wish'
    lines = (reference / 'fixed.pcr').read_text().splitlines()
    job = next(i for i, line in enumerate(lines) if line.startswith('!Job '))
    for i, line in enumerate(tuple(lines)):
        if line.startswith('!Irf Npr Jtyp'):
            lines[i + 1] = ' '.join(lines[i + 1].split()[:3])
    positions = [i for i, line in enumerate(lines) if line.startswith('!2Theta/TOF/E(Kev)')]
    for bank, position in reversed(list(enumerate(positions, start=1))):
        row = lines[job + bank].split('!')[0].split()
        row[3] = '1'
        lines[job + bank] = ' '.join(row)
        last_point = position + int(row[2])
        lines[last_point + 1 : last_point + 1] = [f'! Excluded regions for Pattern# {bank}', '1 2']
        data = f'fixed_{bank}.dat'
        copyfile(reference / data, tmp_path / data)
    source = tmp_path / 'fixed.pcr'
    source.write_text('\n'.join(lines) + '\n')

    headers = [
        line
        for line in export_fixed(source, tmp_path / 'fullprof')
        if line.startswith(('!2Theta/TOF/E(Kev)', '! Excluded regions'))
    ]
    assert headers == [
        heading
        for bank in range(1, 6)
        for heading in (
            f'!2Theta/TOF/E(Kev) Background for Pattern# {bank}',
            f'! Excluded regions (LowT HighT) for Pattern# {bank}',
        )
    ], 'FullProf export writes background and excluded-region sections in source bank order.'


@pytest.mark.parametrize(
    ('case', 'control', 'native_class', 'gap_terms'),
    [
        (
            'pd-neut-cwl_lab6-echidna_fcj-asymmetry',
            'ECH0030684_LaB6_1p622A_fcj',
            'CwlTchPseudoVoigtFcj',
            ('fcj', 'quadrature'),
        ),
        (
            'pd-neut-xray-cwl_pbso4-d1a-lab',
            'fixed',
            'CwlPseudoVoigtBerarBaldinozzi',
            ('beba', 'berar', 'bérar'),
        ),
    ],
)
def test_imported_asymmetry_maps_to_native_profiles_and_reports_the_gap(
    case, control, native_class, gap_terms, tmp_path, capfd
):
    source = REFERENCES / case / f'{control}.pcr'
    imported = Project.load(source)
    captured = capfd.readouterr()
    diagnostic = (captured.out + captured.err).casefold()
    assert 'fullprof' in diagnostic and any(term in diagnostic for term in gap_terms), (
        'Import reports the source-specific asymmetry difference instead of silently '
        'replaying a different native calculation'
    )
    experiment = imported.experiments[0]
    assert type(experiment.peak).__name__ == native_class, (
        'FullProf asymmetry maps onto the existing native profile class'
    )
    lines = source.read_text(encoding='utf-8').splitlines()
    index = next(
        i
        for i, line in enumerate(lines)
        if line.startswith('!') and line[1:].split()[:3] == ['U', 'V', 'W']
    )
    expected = list(map(float, lines[index + 1].split()[:3]))
    actual = [getattr(experiment.peak, 'broad_gauss_' + field).value for field in 'uvw']
    assert actual == pytest.approx(expected), (
        'The native profile retains Caglioti widths read independently from the FullProf control'
    )
    destination = tmp_path / 'native'
    imported.save_as(destination)
    saved = '\n'.join(path.read_text() for path in (destination / 'experiments').glob('*.edi'))
    for retired in ('_peak.fullprof_fcj_limit', '_peak.beba_evaluation', '_peak.fullprof_cw_irf'):
        assert retired not in saved, (
            'A mapped project saves native profiles without retired program-specific maths'
        )
    reopened = Project.load(destination)
    assert type(reopened.experiments[0].peak).__name__ == native_class, (
        'Saving and reopening preserves the mapped native asymmetry profile'
    )


@pytest.mark.parametrize(
    'case',
    ['c15_t2_polarization/lif_single_polarized', 'xray_doublet/absorption/lif_single_absorption'],
)
def test_imported_single_wavelength_xray_project_can_save(case, tmp_path):
    fixture = ROOT / 'tests/fixtures' / f'{case}.pcr'
    source = tmp_path / fixture.name
    rows = fixture.read_text().splitlines()
    rows[0] = 'COMM data_lif_scan'
    heading = next(i for i, line in enumerate(rows) if 'Data for PHASE number' in line)
    title = next(
        i
        for i in range(heading + 1, len(rows))
        if rows[i].strip() and not rows[i].lstrip().startswith('!')
    )
    rows[title] = 'LiF.source'
    source.write_text('\n'.join(rows) + '\n')
    copyfile(fixture.with_suffix('.dat'), source.with_suffix('.dat'))

    project = Project.load(source)
    destination = tmp_path / 'native'
    project.save_as(destination)
    assert (destination / 'structures' / 'LiF_source.edi').is_file(), (
        'Single-wavelength X-ray imports retain their structure file, scalar title '
        'and absent second wavelength.'
    )
    assert '"data_lif_scan"' in (destination / 'project.edi').read_text(), (
        'Single-wavelength X-ray imports retain their structure file, scalar title '
        'and absent second wavelength.'
    )
    exported = export_fixed(destination, tmp_path / 'fullprof')
    index = next(i for i, line in enumerate(exported) if 'Lambda1 Lambda2 Ratio' in line)
    first, second, ratio = map(float, exported[index + 1].split()[:3])
    assert first == second, (
        'Single-wavelength X-ray imports retain their structure file, scalar title '
        'and absent second wavelength.'
    )
    assert ratio == 0, (
        'Single-wavelength X-ray imports retain their structure file, scalar title '
        'and absent second wavelength.'
    )
