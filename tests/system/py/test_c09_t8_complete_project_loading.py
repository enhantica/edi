# ruff: noqa: PLC0415, PT007
# Ported verbatim from the retired hidden fitting-test file ( phase C): the
# body keeps its hidden-tier-authored shape — reshaping it for the visible tier's
# lint would churn what the port must preserve.
"""red-first gates for strict complete loading and fit-example UX."""

from __future__ import annotations

import re
import shutil
import subprocess
from collections.abc import Mapping
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
JOINT_ROOT = ROOT / 'tests/fixtures/c09_t6_ncaf_5bank_absorption'


def _single_project() -> Path:
    from conftest import corpus_case_dir

    return corpus_case_dir('si-sepd-s2') / 'project'


SINGLE_MODEL_ONLY = JOINT_ROOT / 'expected/pre_task_writer/key_absent'
JOINT_MODEL_ONLY = JOINT_ROOT / 'expected/pre_task_writer/e02_t2_ncaf_5bank'
JOINT_ORACLE = JOINT_ROOT / 'crysta_cli_joint_fit.json'
LOCALE_PROBE = ROOT / 'tests/unit/cpp/c09_t8_locale_probe.cpp'
CHANGE_FORMAT_PROBE = ROOT / 'tests/unit/cpp/c09_t8_change_format_probe.cpp'

BANKS = ('wish_1_10', 'wish_2_9', 'wish_3_8', 'wish_4_7', 'wish_5_6')

SINGLE_LABELS = {
    **{
        f'{site}.{leaf}': f'structure.atom_sites[{site}].{leaf}'
        for site, leaf in (
            ('Ca', 'fract_x'),
            ('Al', 'fract_x'),
            ('Na', 'fract_x'),
            ('F1', 'fract_x'),
            ('F1', 'fract_y'),
            ('F1', 'fract_z'),
            ('F2', 'fract_x'),
            ('F2', 'fract_y'),
            ('F2', 'fract_z'),
            ('F3', 'fract_x'),
        )
    },
    **{
        f'{site}.adp_iso': f'structure.atom_sites[{site}].adp_iso'
        for site in ('Ca', 'Al', 'Na', 'F1', 'F2', 'F3')
    },
    'scale': 'experiment.linked_structure.scale',
    'calib_d_to_tof_offset': 'experiment.instrument.calib_d_to_tof_offset',
    'calib_d_to_tof_linear': 'experiment.instrument.calib_d_to_tof_linear',
    'broad_gauss_sigma_2': 'experiment.peak.broad_gauss_sigma_2',
    'rise_alpha_0': 'experiment.peak.rise_alpha_0',
    'rise_alpha_1': 'experiment.peak.rise_alpha_1',
    'decay_beta_0': 'experiment.peak.decay_beta_0',
    'decay_beta_1': 'experiment.peak.decay_beta_1',
}


def _copy_project(tmp_path: Path, source: Path | None = None) -> Path:
    destination = tmp_path / 'project'
    shutil.copytree(_single_project() if source is None else source, destination)
    return destination


def _experiment(project: Path) -> Path:
    experiments = sorted((project / 'experiments').glob('*.edi'))
    assert len(experiments) == 1
    return experiments[0]


def _replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding='utf-8')
    assert text.count(old) == 1
    path.write_text(text.replace(old, new), encoding='utf-8')


def _single_path(label: str) -> str:
    if label in SINGLE_LABELS:
        return SINGLE_LABELS[label]
    background = re.fullmatch(r'background\[(\d+)\]', label)
    assert background is not None, f'unmapped single-bank oracle label {label!r}'
    return f'experiment.background[{background.group(1)}].intensity'


def _joint_path(label: str) -> str:
    bank_match = re.fullmatch(r'([^.]*)\.(.*)', label)
    if bank_match is not None and bank_match.group(1) in BANKS:
        bank, field = bank_match.groups()
        aliases = {
            'calib_d_to_tof_offset': 'instrument.calib_d_to_tof_offset',
            'calib_d_to_tof_linear': 'instrument.calib_d_to_tof_linear',
            'calib_d_to_tof_quadratic': 'instrument.calib_d_to_tof_quadratic',
            'scale': 'linked_structure.scale',
            'abscor1': 'absorption.abscor1',
        }
        background = re.fullmatch(r'background\[(\d+)\]', field)
        if background is not None:
            field = f'background[{background.group(1)}].intensity'
        elif field in aliases:
            field = aliases[field]
        elif not field.startswith((
            'peak.',
            'instrument.',
            'linked_structure.',
            'absorption.',
        )):
            field = f'peak.{field}'  # profile leaves live under the peak category
        return f'experiments[{bank}].{field}'
    if label == 'cell_length_a':
        return 'structure.cell.length_a'
    site, field = label.split('.', maxsplit=1)
    allowed = {'fract_x', 'fract_y', 'fract_z', 'adp_iso', 'occupancy'}
    assert field in allowed, f'unmapped joint oracle label {label!r}'
    return f'structure.atom_sites[{site}].{field}'


def _assert_cli_value(
    actual: float, expected: float, where: str, *, esd: float | None = None
) -> None:
    """Delegate to the ONE shared golden-pin comparator (`conftest.assert_matches_golden_pin`).

    This used to be exact 10-significant-digit STRING equality against an engine-produced golden.
    That is not a tolerance that was too tight - it is a claim that was never true off the
    architecture that minted the pin, and it held only because nothing else ever ran it. The
    comparator and its reasoning live in one place so this file and its sibling
    (`test_c09_t6_joint_multibank_absorption.py`) cannot drift apart again.
    """
    from conftest import assert_matches_golden_pin

    assert_matches_golden_pin(actual, expected, where, esd=esd)


def test_c09_t8_joint_one_call_fit_reuses_the_full_value_set(
    session_joint_fit,
) -> None:
    """The one-call joint surface exposes the COMPLETE value/ESD layout (P1.2b: F-live).

    Renamed from `reuses_all_193_c09_t6_values` with the re-frozen oracle (ruling 7a/8a): the
    expected table is the ruled vehicle's committed F-rec golden — the like-config crysta CLI
    record — and the fit is the session's ONE shared producer run, never re-run here. The
    stale-ESD re-oracle (inherited red 2) lands with this change: every ESD is cited from the
    regenerated reference. The movement witness derives from the case's committed project files.
    """
    from conftest import corpus_case_dir, frec_golden_record

    golden = frec_golden_record('ncaf-wish-3bank-s5', 'joint-default')
    expected = {}
    for key, value in golden.items():
        if key.startswith('param.') and key.endswith('.value'):
            label = key.removeprefix('param.').removesuffix('.value')
            expected[_joint_path(label)] = {
                'value': float(value),
                'esd': float(golden[f'param.{label}.esd']),
            }
    result = session_joint_fit.outcome
    assert len(expected) == len(result.values) == int(golden['n_free']), (
        'the fit result must retain every independently frozen parameter'
    )
    assert set(result.values) == set(result.uncertainty) == set(expected), (
        'the fit values and uncertainties must retain identical parameter keys'
    )

    # Independent declared input: the fit must move this surviving result value.
    scale_line = next(
        line
        for line in (
            corpus_case_dir('ncaf-wish-3bank-s5') / 'project' / 'experiments' / 'wish_5_6.edi'
        )
        .read_text(encoding='utf-8')
        .splitlines()
        if line.startswith('ncaf ')
    )
    declared_scale = float(scale_line.split()[1].split('(')[0])
    assert result.values['experiments[wish_5_6].linked_structure.scale'] != pytest.approx(
        declared_scale, abs=0.0
    ), 'the joint fit must move the declared surviving scale value'

    for path, row in expected.items():
        _assert_cli_value(float(result.values[path]), row['value'], path, esd=row['esd'])
        _assert_cli_value(float(result.uncertainty[path]), row['esd'], path + '.uncertainty')

    banks = {bank.name: bank for bank in result.banks}
    golden_banks = {
        key.removeprefix('bank.').removesuffix('.n_points')
        for key in golden
        if key.startswith('bank.') and key.endswith('.n_points')
    }
    assert set(banks) == golden_banks, ': the joint fit must report the golden bank set'
    assert len(banks) == 3, ': the joint fit must report all three banks'
    assert sum(bank.n_points for bank in banks.values()) == int(golden['n_points_fitted']), (
        ': the bank point counts must sum to the golden fitted-point total'
    )
    for name, bank in banks.items():
        assert bank.n_points == int(golden[f'bank.{name}.n_points']), (
            ': each bank must keep its golden per-bank point count'
        )
        _assert_cli_value(float(bank.rwp), float(golden[f'bank.{name}.rwp']), f'{name}.rwp')
        _assert_cli_value(
            float(bank.chi_square),
            float(golden[f'bank.{name}.chi_square']),
            f'{name}.chi_square',
        )
    assert len({float(bank.rwp) for bank in banks.values()}) == 3, (
        ': the three banks must report three distinct Rwp values'
    )
    assert all(float(bank.rwp) != pytest.approx(float(result.rwp)) for bank in banks.values()), (
        ': no per-bank Rwp may collapse onto the joint Rwp'
    )


def test_c09_t8_one_loader_rejects_zero_experiments(
    tmp_path: Path,
) -> None:
    import edi

    project = _copy_project(tmp_path)
    analysis = project / 'analysis' / 'analysis.edi'
    analysis_lines = analysis.read_text(encoding='utf-8').splitlines()
    # Old saved projects had a trailing fit-parameter loop. Current canonical
    # projects may contain only the fitting mode and minimizer settings.
    if '_fit_parameter.id' in analysis_lines:
        fit_parameter_header = analysis_lines.index('_fit_parameter.id')
        assert analysis_lines[fit_parameter_header - 1] == 'loop_', (
            ': removing a fit-parameter loop must preserve valid analysis syntax'
        )
        analysis.write_text(
            '\n'.join(analysis_lines[: fit_parameter_header - 1]) + '\n',
            encoding='utf-8',
        )
    shutil.rmtree(project / 'experiments')
    with pytest.raises(edi.IoError, match=r'(?i)(complete|experiment)'):
        edi.Project.load(project)


@pytest.mark.parametrize('source', (SINGLE_MODEL_ONLY, JOINT_MODEL_ONLY), ids=('single', 'joint'))
def test_c09_t8_one_loader_rejects_every_data_less_bank(
    source: Path,
) -> None:
    import edi

    with pytest.raises(edi.IoError, match=r'(?i)(complete|experiment|embedded|data)'):
        edi.Project.load(source)


@pytest.mark.parametrize('defect', ('omitted', 'misspelled'))
def test_c09_t8_missing_tof_column_fails_during_the_one_load_mode(
    tmp_path: Path,
    defect: str,
) -> None:
    import edi

    project = _copy_project(tmp_path)
    path = _experiment(project)
    lines = path.read_text(encoding='utf-8').splitlines()
    header = lines.index('_data.time_of_flight')
    if defect == 'omitted':
        row_start = header
        while row_start < len(lines) and lines[row_start].startswith('_data.'):
            row_start += 1
        columns = lines[header:row_start]
        column_count = len(columns)
        assert column_count >= 3, 'the missing-axis vehicle needs measured data columns'
        row_end = row_start
        while row_end < len(lines) and lines[row_end].strip() and lines[row_end] != 'loop_':
            row_end += 1
        rows = [lines[index].split() for index in range(row_start, row_end)]
        for fields in rows:
            assert len(fields) == column_count, (
                'the source data rows must match their declared columns before the axis is removed'
            )
        axis_column = columns.index('_data.time_of_flight')
        measured_column = columns.index('_data.intensity_meas')
        uncertainty_column = columns.index('_data.intensity_meas_su')
        # An experiment.data getter is linked to its source; use a detached data value as
        # the counterfactual's measured input, then edit only this copied project file.
        detached = edi.PdTofData(
            time_of_flight=[float(row[axis_column]) for row in rows],
            intensity_meas=[float(row[measured_column]) for row in rows],
            intensity_meas_su=[float(row[uncertainty_column]) for row in rows],
        )
        for offset, index in enumerate(range(row_start, row_end)):
            fields = rows[offset]
            fields[measured_column] = str(detached.intensity_meas[offset])
            fields[uncertainty_column] = str(detached.intensity_meas_su[offset])
            lines[index] = ' '.join(fields[1:])
        lines.pop(header)
    else:
        lines[header] = '_data.time_of_fight'
    assert '_data.intensity_meas' in lines, (
        'the missing-axis counterfactual must retain the measured-intensity column'
    )
    assert '_data.intensity_meas_su' in lines, (
        'the missing-axis counterfactual must retain the measured-uncertainty column'
    )
    path.write_text('\n'.join(lines) + '\n', encoding='utf-8')

    with pytest.raises(edi.IoError, match=r'_data\.time_of_flight'):
        edi.Project.load(project)


def test_c09_t8_unknown_dictionary_covered_tag_is_rejected(tmp_path: Path) -> None:
    import edi

    project = _copy_project(tmp_path)
    _replace_once(
        _experiment(project),
        '_peak.type tof-jorgensen-von-dreele\n',
        '_peak.type tof-jorgensen-von-dreele\n_peak.not_a_real_tag 1\n',
    )
    with pytest.raises(edi.IoError, match=r'(?i)(unknown|peak).*not_a_real_tag'):
        edi.Project.load(project)


def test_c09_t8_classic_numeric_corpus_and_comma_counterfactual_are_deterministic(
    tmp_path: Path,
) -> None:
    compiler = shutil.which('c++')
    assert compiler is not None, 'the pinned C++ compiler is required for the locale probe'
    executable = tmp_path / 'locale-probe'
    build = subprocess.run(
        [compiler, '-std=c++20', str(LOCALE_PROBE), '-o', str(executable)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert build.returncode == 0, build.stdout + build.stderr
    run = subprocess.run(
        [str(executable)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert run.returncode == 0, run.stdout + run.stderr


def test_c09_t8_writer_round_trips_presence_of_embedded_data(tmp_path: Path) -> None:
    """Measured data survives save/reload; clearing it writes an unloadable project.

    The one loader makes the latter direction an explicit refusal: a saved experiment must
    declare measured data or a calculation range before it can be loaded again.
    """
    import edi

    project = edi.Project.load(_single_project())
    destination = tmp_path / 'saved'
    project.save_as(destination)
    assert any('_data.' in path.read_text(encoding='utf-8') for path in destination.rglob('*.edi'))
    restored = edi.Project.load(destination)
    assert all(experiment.data is not None for experiment in restored.experiments)

    # Strip the data and prove the writer does not fabricate an observation; the one loader then
    # refuses because the resulting experiment declares neither category.
    for experiment in project.experiments:
        experiment.data = None
    stripped = tmp_path / 'stripped'
    project.save_as(stripped)
    assert all(
        '_data.' not in path.read_text(encoding='utf-8') for path in stripped.rglob('*.edi')
    )
    with pytest.raises(edi.IoError, match=r'(?i)(complete|embedded|data)'):
        edi.Project.load(stripped)


def test_c09_t8_existing_constructors_and_model_only_fit_signatures_remain_available() -> None:
    # P1.2b (F-cheap): the model-only signature runs on the cheapest corpus case, whose measured
    # pattern is embedded in the project rather than passed beside it.
    import edi

    from conftest import corpus_case_dir

    assert callable(edi.StructureFactory.from_dict), (
        'the existing dictionary constructor must remain publicly callable'
    )
    project = edi.Project.load(corpus_case_dir('cosio-d20-s1') / 'project')
    data = project.experiments[0].data
    assert data is not None, 'the model-only fit witness must carry embedded measured data'
    result = project.fit()
    assert isinstance(result.values, Mapping), 'the model-only fit must retain mapped results'
    assert result.converged is True, 'the model-only fit must retain convergence behavior'
