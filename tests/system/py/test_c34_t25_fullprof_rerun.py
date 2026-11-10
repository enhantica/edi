"""Static checks of the committed  FullProf authoring evidence.

Owner ruling 2026-09-25: no test executes FullProf, locally or in CI.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import shutil
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[3]
spec = importlib.util.spec_from_file_location(
    'c34_layout', ROOT / 'tests/integration/py/test_c34_t25_fullprof_layout.py'
)
contract = importlib.util.module_from_spec(spec)
spec.loader.exec_module(contract)


def normalized(text):
    # Independent 8.40 reruns change only the expected-Rp statistics below;
    # measured Rp/cRp (the Observed suffix), Rwp, Rexp, chi2 and all parameters
    # still compare exactly. DAT file code names the invocation alias, not data.
    text = re.sub(r'\d{2}/\d{2}/\d{4}\s*/?\s+\d{2}:\d{2}:\d{2}\.\d+', '<run-date>', text)
    text = re.sub(r'(=> DAT file code:)\s*\S+\s*(->)', r'\1 <data-file> \2', text)
    text = re.sub(
        r'(Expected c?Rp ?\(background\s+(?:un)?corrected\):)\s*' + contract.FLOAT,
        r'\1 <run-dependent-expected-Rp>',
        text,
    )
    text = re.sub(
        r'(-> Ratio Rp/Exp=cRp/cExp:)\s*' + contract.FLOAT,
        r'\1 <run-dependent-ratio>',
        text,
    )
    return '\n'.join(
        line.rstrip()
        for line in text.splitlines()
        if not re.search(r'(?i)(date:|date and time|cpu[- ]time|total time)', line)
        and not re.fullmatch(r'\s*\d+\.\d+ minutes\s*', line)
    )


def test_output_normalization_preserves_observations_and_fit_parameters():
    # Representative FullProf fields: volatile diagnostics may vary, whereas
    # observed residuals, data weighting and fit parameters must remain exact.
    source = (
        ' => DAT file code: scale-fit -> Relative contribution: 1.0000\n'
        '  Expected Rp (background uncorrected): 1.86 Observed-> 6.09\n'
        '  Expected cRp(background corrected): 3.70 Observed-> 12.10\n'
        '  -> Ratio Rp/Exp=cRp/cExp: 3.27\n'
        '  Rwp: 7.02 Rexp: 2.69 Chi2: 3.88\n'
        '  Direct cell parameters: 8.4780\n'
    )
    for old, new in [
        ('scale-fit', 'actual-data'),
        ('1.86', '1.91'),
        ('3.70', '3.80'),
        ('3.27', '3.19'),
    ]:
        assert normalized(source.replace(old, new)) == normalized(source), (
            ' only independent-run labels and expected-Rp statistics may vary'
        )
    for old in ['1.0000', '6.09', '12.10', '7.02', '2.69', '3.88', '8.4780']:
        assert normalized(source.replace(old, '99.99')) != normalized(source), (
            ' normalized output must retain observations, weights and structure'
        )


def check_artifact_provenance(directory):
    text = (directory / 'PROVENANCE.md').read_text()
    assert re.search(r'FullProf\.2k 8\.40', text), (
        ' provenance must name the authoring FullProf version 8.40'
    )
    commands = re.findall(r'`([^`]*\bfp2k\b[^`]*)`', text)
    pcr = next(directory.glob('*.pcr'))
    assert any(pcr.stem in command for command in commands), (
        ' provenance must record the FullProf command and PCR input'
    )
    rows = re.findall(r'^- `([^`]+)` `([a-f0-9]{64})`$', text, re.MULTILINE)
    pins = dict(rows)
    files = {p.name for p in directory.iterdir() if p.is_file() and p.name != 'PROVENANCE.md'}
    assert len(rows) == len(pins) and set(pins) == files, (
        ' provenance sha256 inventory must cover every input and output exactly once'
    )
    assert {pcr.name, pcr.with_suffix('.prf').name, pcr.with_suffix('.sum').name} <= files, (
        ' every project must retain its PCR and matched PRF/SUM artifacts'
    )
    for name, digest in pins.items():
        assert hashlib.sha256((directory / name).read_bytes()).hexdigest() == digest, (
            ' committed input/output bytes must match authoring provenance sha256'
        )


@pytest.mark.parametrize(('home', 'name'), contract.PROJECTS)
def test_committed_artifacts_match_authoring_provenance(home, name):
    directory, _, _ = contract.project(home, name)
    check_artifact_provenance(directory)


def check_saved_fit(directory, pcr, data, home):
    if not contract.requires_refit(home, directory.name):
        contract.check_unchanged_inputs(directory, pcr, directory.name)
        return
    assert data.get('fit_out'), ' changed projects and twins must retain fit evidence'
    names = data['fit_out']
    names = [names] if isinstance(names, str) else names
    for filename in names:
        contract.fit_record(directory, filename, contract.parse_pcr(pcr.read_text()), data, home)
        assert 'Version 8.40' in (directory / filename).read_text(), (
            ' saved post-conversion fit must identify FullProf 8.40'
        )


@pytest.mark.parametrize(('home', 'name'), contract.PROJECTS)
def test_saved_fit_artifacts_and_unchanged_inputs(home, name):
    directory, pcr, _ = contract.project(home, name)
    check_saved_fit(directory, pcr, contract.evidence(directory), home)


@pytest.mark.parametrize(
    'name', ['pd-neut-tof_diamond-dream_basic', 'pd-neut-cwl_lab6-11b-echidna_tch-fcj']
)
def test_changed_project_and_k_one_twin_cannot_omit_fit_evidence(name):
    directory, pcr, _ = contract.project('verification', name)
    data = contract.evidence(directory)
    data.pop('fit_out')
    with pytest.raises(AssertionError, match='must retain fit evidence'):
        check_saved_fit(directory, pcr, data, 'verification')


@pytest.mark.parametrize('extension', ['.pcr', '.prf', '.sum', '.inp', '.out'])
def test_authoring_pins_reject_changed_inputs_and_outputs(tmp_path, extension):
    source, _, _ = contract.project('verification', 'pd-neut-tof_diamond-dream_basic')
    directory = tmp_path / source.name
    shutil.copytree(source, directory)
    check_artifact_provenance(directory)
    output = next(directory.glob('*' + extension))
    output.write_bytes(output.read_bytes() + b'\nchanged scientific artifact\n')
    with pytest.raises(AssertionError, match='authoring provenance sha256'):
        check_artifact_provenance(directory)


def read_ralf(path):
    lines = path.read_text().splitlines()
    bank = next(i for i, line in enumerate(lines) if line.startswith('BANK'))
    count = int(lines[bank].split()[2])
    rows = []
    for line in lines[bank + 1 :]:
        for i in range(0, len(line), 20):
            chunk = line[i : i + 20]
            if chunk.strip():
                rows.append([float(chunk[:8]) / 32, float(chunk[8:15]), float(chunk[15:20])])
    assert len(rows) == count, ' independent RALF reader must preserve every fixed-width triple'
    return np.array(rows)


def profile(path):
    rows = []
    started = False
    for line in path.read_text().splitlines():
        if 'Yobs' in line or line == 'BEGIN':
            started = True
            continue
        if started:
            try:
                row = [float(v) for v in line.split()[:4]]
            except ValueError:
                continue
            if len(row) == 4:
                rows.append(row)
    assert rows, ' PRF must expose measured and calculated intensities'
    return np.array(rows)


def pearl_data():
    directory, pcr, parsed = contract.project('verification', 'pd-neut-tof_ceo2-pearl_polynomial')
    assert parsed['Ins'] == 10, ' PEARL must consume explicit X Y sigma data'
    dat = next(p for p in directory.glob('*.dat') if 'XYDATA' in p.read_text()[:300])
    rows = []
    for line in dat.read_text().splitlines():
        if line.strip() and not line.startswith(('!', '#')):
            try:
                vals = list(map(float, line.split()))
            except ValueError:
                continue
            if len(vals) == 3:
                rows.append(vals)
    xy = np.array(rows)
    ralf = read_ralf(contract.FIX / 'Ceo2_PEARL.ralf')
    assert xy.shape == ralf.shape == (2524, 3), ' XYDATA must retain all 2524 original RALF points'
    assert np.array_equal(xy[:, 0], ralf[:, 0]), ' X must equal RALF TOF divided by 32 exactly'
    assert np.all(xy[:, 2] > 0), ' sigma values must remain positive'
    return directory, pcr, dat, xy, ralf


def test_pearl_xydata_preserves_static_ralf_data():
    _, _, _, xy, ralf = pearl_data()
    assert xy[:, 2] == pytest.approx(ralf[:, 2] * xy[:, 1] / ralf[:, 1], rel=1e-6), (
        ' sigma must receive exactly the same pointwise normalization as intensity'
    )


def check_pearl_authoring_snapshot(pcr):
    saved = contract.FIX / 'pearl-authoring'
    manifest = json.loads((saved / 'manifest.json').read_text())
    assert manifest['version'] == 'FullProf.2k 8.40', (
        ' PEARL independent authoring snapshot must identify FullProf 8.40'
    )
    assert manifest['command'] == ['fp2k', 'Ceo2_PEARL', 'Ceo2_PEARL'], (
        ' PEARL snapshot must retain its authoring command and input names'
    )
    assert set(manifest['sha256']) == {
        'Ceo2_PEARL.inp',
        'Ceo2_PEARL.prf',
        'Ceo2_PEARL.sum',
        'Ceo2_PEARL.out',
    }, ' PEARL snapshot hashes must cover its input and every retained output'
    for name, digest in manifest['sha256'].items():
        assert hashlib.sha256((saved / name).read_bytes()).hexdigest() == digest, (
            ' PEARL authoring input/output snapshot must retain its recorded bytes'
        )
    assert (
        manifest['data_sha256']
        == hashlib.sha256((contract.FIX / 'Ceo2_PEARL.ralf').read_bytes()).hexdigest()
    ), ' PEARL authoring run must bind the original RALF data'
    original = contract.parameter_records((saved / 'Ceo2_PEARL.inp').read_text())
    current = contract.parameter_records(pcr.read_text())
    # FullProf rewrites the PCR sampling range after reading each format.
    # These are sampling metadata, checked against each profile below.
    original['values'].pop('range')
    current['values'].pop('range')
    assert original['values'] == current['values'], (
        ' RALF and XYDATA committed profiles must use identical physical parameters'
    )
    assert contract.parse_pcr((saved / 'Ceo2_PEARL.inp').read_text())['Ins'] == 12, (
        ' independent observed profile must come from the RALF reader'
    )
    out = (saved / 'Ceo2_PEARL.out').read_text()
    assert 'Version 8.40' in out, ' saved PEARL OUT must identify FullProf 8.40'
    assert re.findall(r'Number of Least-Squares parameters varied:\s*(\d+)', out) == ['0'], (
        ' PEARL comparison must not refit the RALF parameters'
    )
    return saved


def test_pearl_committed_profiles_preserve_data_and_correct_weights():
    directory, pcr, _, xy, ralf = pearl_data()
    saved = check_pearl_authoring_snapshot(pcr)
    obs = profile(saved / 'Ceo2_PEARL.prf')
    calc = profile(pcr.with_suffix('.prf'))
    # IGOR prints TOF to three decimals. XYDATA versus raw RALF above stays exact;
    # this join permits only the independent output format's half-last-digit rounding.
    indices = np.abs(xy[:, 0, None] - obs[None, :, 0]).argmin(axis=0)
    assert len(set(indices)) == len(indices), ' every RALF profile point must join uniquely'
    assert xy[indices, 0] == pytest.approx(obs[:, 0], rel=0, abs=0.00051), (
        ' profile coordinates may differ only by IGOR decimal rounding'
    )
    assert xy[indices, 1] == pytest.approx(obs[:, 1], rel=1e-6), (
        ' Y must retain FullProf RALF Yobs point by point'
    )
    assert xy[:, 2] == pytest.approx(ralf[:, 2] * xy[:, 1] / ralf[:, 1], rel=1e-6), (
        ' sigma must receive exactly the same pointwise normalization as intensity'
    )
    bank = next(
        line
        for line in (contract.FIX / 'Ceo2_PEARL.ralf').read_text().splitlines()
        if line.startswith('BANK')
    ).split()
    last_y = ralf[-1, 1] / (10 * float(bank[8]) * ralf[-1, 0])
    assert xy[-1, 1] == pytest.approx(last_y, rel=1e-6), (
        ' terminal RALF point must retain the declared header dt/t normalization'
    )
    # FullProf's RALF reader omits the final source triple. XYDATA must retain
    # it; compare Icalc on ALL RALF-observed coordinates, without dropping a
    # source point from either the converted data or its independent profile.
    assert calc[:, 0] == pytest.approx(xy[:, 0], rel=0, abs=0.00051), (
        ' XYDATA calculated profile must retain every converted coordinate'
    )
    assert np.array_equal(obs[:, 0], calc[indices, 0]), (
        ' every RALF calculated point must share its converted coordinate'
    )
    assert calc[indices, 2] == pytest.approx(obs[:, 2], rel=1e-3), (
        ' Icalc must agree at identical parameters'
    )
    # FullProf Rexp uses the fitted region after excluding the two declared intervals.
    mask = (xy[:, 0] > 2000) & (xy[:, 0] < 18700)
    expected = 100 * np.sqrt(mask.sum() / np.sum((xy[mask, 1] / xy[mask, 2]) ** 2))

    def rexp(mode):
        text = (
            (saved if mode == 'ralf' else directory) / pcr.with_suffix('.sum').name
        ).read_text()
        values = re.findall(r'Rexp:\s*(' + contract.FLOAT + ')', text)
        assert values, ' FullProf SUM must report Rexp'
        return float(values[0])

    assert rexp('xy') == pytest.approx(expected, rel=0.01), (
        ' XYDATA Rexp must agree with file sigma within one percent'
    )
    assert rexp('ralf') == pytest.approx(100 * expected, rel=0.01), (
        ' committed RALF run must expose the hundredfold Rexp defect'
    )
