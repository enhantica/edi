"""P4: save-by-default, byte-clean dry runs, and reversible undo."""

from __future__ import annotations

import contextlib
import hashlib
import importlib
import os
import re
import shutil
import subprocess
import sys
from itertools import product
from pathlib import Path
from typing import Any

import pytest

from conftest import (
    crysta_reference_prefix,
    crysta_reference_source,
    project_record_datetime,
    project_record_value,
    project_record_without_fields,
    project_tree_parts,
)
from tests.fixtures.ncaf_free_flags import canonicalize

ROOT = Path(__file__).resolve().parents[3]
LIB = importlib.import_module('edi')


def _crysta_root() -> Path:
    candidates = []
    override = os.environ.get('EDI_CRYSTA_CORPUS_ROOT')
    if override:
        candidates.append(Path(override).resolve().parents[1])
    candidates.extend((ROOT, crysta_reference_source()))
    for candidate in candidates:
        if (candidate / 'tests/fitting/manifest.yml').is_file():
            return candidate
    message = "the  CLI gate requires crysta's committed fitting corpus"
    raise AssertionError(message)


def _crysta_cli() -> Path:
    override = os.environ.get('E09_T58_CRYSTA_CLI')
    if override:
        executable = Path(override)
        assert executable.is_file(), (
            'the historical positional-writeback subject must name a built crysta CLI'
        )
        return executable
    if LIB.__name__ == 'edi':
        executable = crysta_reference_prefix() / 'bin/crysta'
        assert executable.is_file(), 'edi core-build must install the comparison crysta CLI'
        return executable
    candidates = sorted((ROOT / 'build').glob('cp312-abi3*/crysta'))
    assert candidates, 'crysta cpp-build must produce its native CLI'
    return candidates[0]


def _local_cli() -> list[str]:
    if LIB.__name__ == 'edi':
        return [sys.executable, '-m', 'edi']
    return [str(_crysta_cli())]


def _stage_project(destination: Path, *, starting_uncertainty: str = '40') -> Path:
    source = _crysta_root() / 'tests/fitting/lbco-hrpt-s2/project'
    shutil.copytree(source, destination)
    analysis = destination / 'analysis/analysis.edi'
    analysis_text = analysis.read_text(encoding='utf-8')
    assert '_minimizer.max_iterations 1000' in analysis_text, (
        'the staged corpus analysis must expose the canonical budget before test mutation'
    )
    analysis.write_text(
        analysis_text.replace('_minimizer.max_iterations 1000', '_minimizer.max_iterations 1'),
        encoding='utf-8',
    )
    structure = destination / 'structures/lbco.edi'
    structure_text = structure.read_text(encoding='utf-8')
    assert '_cell.length_a 3.88()' in structure_text, (
        'the staged structure must expose its pre-fit cell value before uncertainty injection'
    )
    structure.write_text(
        structure_text.replace(
            '_cell.length_a 3.88()',
            f'_cell.length_a 3.880({starting_uncertainty})',
        ),
        encoding='utf-8',
    )
    return destination


def _stage_positional_project(destination: Path) -> Path:
    case = _crysta_root() / 'tests/fitting/ncaf-wish-3bank-s5'
    shutil.copytree(case / 'project', destination)
    structure = destination / 'structures/ncaf.edi'
    structure.write_text(canonicalize(structure.read_text()))
    bounded = (case / 'bounded-analysis/analysis.edi').read_text(encoding='utf-8')
    assert '_minimizer.max_iterations 2' in bounded, (
        'the positional-basic witness must retain its independently declared bounded fit'
    )
    (destination / 'analysis/analysis.edi').write_text(bounded, encoding='utf-8')
    return destination


def _site(project_dir: Path, site_id: str) -> Any:
    matches = [
        site for site in LIB.Project.load(project_dir).structure.atom_sites if site.id == site_id
    ]
    assert len(matches) == 1, f'expected one atom site {site_id!r}, found {len(matches)}'
    return matches[0]


def _site_parameter_token(project_dir: Path, site_id: str, tag: str) -> str:
    structure = next((project_dir / 'structures').glob('*.edi'))
    lines = structure.read_text(encoding='utf-8').splitlines()
    tag_index = lines.index(tag)
    loop_index = max(index for index, line in enumerate(lines[:tag_index]) if line == 'loop_')
    tags = []
    row_index = loop_index + 1
    while row_index < len(lines) and lines[row_index].startswith('_'):
        tags.append(lines[row_index])
        row_index += 1
    column = tags.index(tag)
    row = next(line.split() for line in lines[row_index:] if line.split()[:1] == [site_id])
    return row[column]


def _machine_number(record: str, key: str) -> float:
    matches = re.findall(rf'^{re.escape(key)}=(\S+)$', record, re.MULTILINE)
    assert len(matches) == 1, f'the fit machine record must contain exactly one {key!r}'
    return float(matches[0])


def _tree_bytes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob('*'))
        if path.is_file()
    }


def _run(command: list[str], *arguments: str) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        [*command, *arguments],
        cwd=ROOT,
        env=os.environ.copy(),
        capture_output=True,
        text=True,
        timeout=180,
        check=False,
    )
    assert completed.returncode == 0, (
        'every CLI action in the reversible fit unit must succeed; '
        + completed.stdout
        + completed.stderr
    )
    return completed


def _parameter(project_dir: Path) -> Any:
    return LIB.Project.load(project_dir).structure.cell.length_a


def _assert_uncertainty_presence_round_trip(tmp_path: Path) -> None:
    absent = _stage_project(tmp_path / 'absent-uncertainty', starting_uncertainty='')
    explicit_zero = _stage_project(tmp_path / 'zero-uncertainty', starting_uncertainty='0')
    assert _parameter(absent).uncertainty is None, (
        'the absence witness must begin with a refinable parameter whose uncertainty is absent'
    )
    assert float(_parameter(explicit_zero).uncertainty) == pytest.approx(0.0), (
        'the zero witness must begin with an explicit numeric zero uncertainty'
    )

    absent_saved = tmp_path / 'absent-saved'
    zero_saved = tmp_path / 'zero-saved'
    LIB.Project.load(absent).save_as(absent_saved)
    LIB.Project.load(explicit_zero).save_as(zero_saved)
    assert _parameter(absent_saved).uncertainty is None, (
        'save and load must preserve absent uncertainty as absent'
    )
    assert float(_parameter(zero_saved).uncertainty) == pytest.approx(0.0), (
        'save and load must preserve explicit zero uncertainty as numeric zero'
    )

    _run(_local_cli(), 'fit', str(absent), '--verbosity', 'off')
    _run(_local_cli(), 'fit', str(explicit_zero), '--verbosity', 'off')
    captured_absent = _parameter(absent).start_uncertainty
    captured_zero = _parameter(explicit_zero).start_uncertainty
    _run(_local_cli(), 'undo', str(absent))
    _run(_local_cli(), 'undo', str(explicit_zero))
    assert captured_absent is None, (
        'fit/save/load must retain an absent pre-fit uncertainty in the persisted undo snapshot'
    )
    assert float(captured_zero) == pytest.approx(0.0), (
        'fit/save/load must retain explicit zero in the persisted undo snapshot'
    )
    assert _parameter(absent).uncertainty is None, (
        'undo must restore absent uncertainty as absent rather than inventing numeric zero'
    )
    assert float(_parameter(explicit_zero).uncertainty) == pytest.approx(0.0), (
        'undo must restore an explicit zero uncertainty as numeric zero'
    )


def test_local_fit_dry_and_undo_are_one_reversible_unit(tmp_path: Path) -> None:
    dry = _stage_project(tmp_path / 'dry')
    before_dry = _tree_bytes(dry)
    _run(_local_cli(), 'fit', str(dry), '--verbosity', 'off', '--dry')
    assert _tree_bytes(dry) == before_dry, '--dry must leave every directory byte unchanged'

    fitted = _stage_project(tmp_path / 'fitted')
    before_fit = _tree_bytes(fitted)
    _run(_local_cli(), 'fit', str(fitted), '--verbosity', 'off')
    assert _tree_bytes(fitted) != before_fit, 'fit must save the refined project by default'

    refined = _parameter(fitted)
    assert (float(refined.value), float(refined.uncertainty)) != pytest.approx((3.88, 0.04)), (
        'save-by-default must persist a fitted value and uncertainty distinct from the start state'
    )

    first = _run(_local_cli(), 'undo', str(fitted))
    assert 'was_no_op=false' in first.stdout, (
        'the first undo must report that it restored persisted pre-fit state'
    )
    restored = _parameter(fitted)
    assert float(restored.value) == pytest.approx(3.88), (
        'undo must restore the project value recorded before refinement'
    )
    assert float(restored.uncertainty) == pytest.approx(0.04), (
        'undo must restore the project uncertainty recorded before refinement'
    )

    before_second = _tree_bytes(fitted)
    second = _run(_local_cli(), 'undo', str(fitted))
    assert 'was_no_op=true' in second.stdout, (
        'a second undo must report that no prior fit state remains'
    )
    assert _tree_bytes(fitted) == before_second, 'a second undo reports and performs a no-op'

    _assert_uncertainty_presence_round_trip(tmp_path)


def test_positional_basic_fit_reaches_model_file_and_undo(tmp_path: Path) -> None:
    fitted = _stage_positional_project(tmp_path / 'positional-basic')
    starting = _site(fitted, 'Ca1').fract_x
    starting_value = float(starting.value)
    starting_uncertainty = float(starting.uncertainty)
    starting_token = _site_parameter_token(fitted, 'Ca1', '_atom_site.fract_x')

    arguments = ['fit', str(fitted), '--verbosity', 'full']
    if LIB.__name__ == 'edi':
        arguments.extend(('--report', 'machine'))
    record = _run(_local_cli(), *arguments).stdout
    expected_value = _machine_number(record, 'param.Ca1.fract_x.value')
    expected_uncertainty = _machine_number(record, 'param.Ca1.fract_x.uncertainty')
    assert expected_value != pytest.approx(starting_value), (
        'the bounded fit must actually move the positional basic under test'
    )

    fitted_token = _site_parameter_token(fitted, 'Ca1', '_atom_site.fract_x')
    assert fitted_token != starting_token, (
        'the structures file must carry the moved positional-basic coordinate'
    )
    assert '(' in fitted_token, (
        'the structures file must serialize an e.s.d. with the moved positional basic'
    )
    restored = _site(fitted, 'Ca1').fract_x
    assert float(restored.value) == pytest.approx(expected_value), (
        'the positional-basic value from the machine record must reach the saved model'
    )
    assert float(restored.uncertainty) == pytest.approx(expected_uncertainty), (
        'the positional-basic e.s.d. from the machine record must reach the saved model'
    )
    _run(_local_cli(), 'undo', str(fitted), '--verbosity', 'off')
    undone = _site(fitted, 'Ca1').fract_x
    assert float(undone.value) == pytest.approx(starting_value), (
        'undo must return the positional basic to its pre-fit model value'
    )
    assert float(undone.uncertainty) == pytest.approx(starting_uncertainty), (
        'undo must return the positional basic to its pre-fit model e.s.d.'
    )
    assert _site_parameter_token(fitted, 'Ca1', '_atom_site.fract_x') == starting_token, (
        'undo must restore the pre-fit positional-basic value and e.s.d. in the file'
    )


def _coordinate_state(project_dir: Path) -> dict[str, tuple[float, float | None]]:
    return {
        f'{site.id}.{axis}': (float(parameter.value), parameter.uncertainty)
        for site in LIB.Project.load(project_dir).structure.atom_sites
        for axis in ('fract_x', 'fract_y', 'fract_z')
        for parameter in (getattr(site, axis),)
    }


def _fit_snapshot_ids(project_dir: Path) -> list[str]:
    lines = (project_dir / 'analysis/analysis.edi').read_text(encoding='utf-8').splitlines()
    header = lines.index('_fit_parameter.id')
    row = header + 1
    while row < len(lines) and lines[row].startswith('_'):
        row += 1
    identifiers = []
    for line in lines[row:]:
        if not line.strip() or line.startswith(('loop_', '_', 'data_')):
            break
        identifiers.append(line.split()[0])
    return identifiers


@pytest.mark.parametrize('mode', ['memory', 'saved'])
def test_edi_tied_coordinates_allow_a_second_fit(tmp_path: Path, mode: str) -> None:
    # Review-8 F1: the independently declared equal-coordinate group has one basic even though
    # all three model members participate in completion. A completed fitted state must remain a
    # valid input to the next fit, both directly and after the writer/loader boundary.
    staged = _stage_positional_project(tmp_path / mode)
    project = LIB.Project.load(staged)
    first = project.fit_joint()
    assert first.values, 'F1 the bounded first edi fit must produce fitted model values'

    site = next(item for item in project.structure.atom_sites if item.id == 'Al1')
    axes = [site.fract_x, site.fract_y, site.fract_z]
    assert sum(parameter.start_value is not None for parameter in axes) == 1, (
        'F1 an equal-coordinate group must retain exactly one pre-fit snapshot basic in memory'
    )

    if mode == 'saved':
        saved = tmp_path / 'saved'
        project.save_as(saved)
        snapshot_ids = _fit_snapshot_ids(saved)
        assert len(snapshot_ids) == len(set(snapshot_ids)), (
            'F1 persisted pre-fit snapshot identifiers must remain unique'
        )
        assert sum(name.startswith('structure.Al1.fract_') for name in snapshot_ids) == 1, (
            'F1 persisted equal coordinates must occupy one snapshot row rather than three'
        )
        project = LIB.Project.load(saved)

    second = project.fit_joint()
    assert second.values, 'F1 a second edi fit must complete without refusing tied coordinates'
    site = next(item for item in project.structure.atom_sites if item.id == 'Al1')
    assert (
        sum(
            parameter.start_value is not None
            for parameter in (site.fract_x, site.fract_y, site.fract_z)
        )
        == 1
    ), 'F1 the second fit must replace the equal-coordinate snapshot with one new basic'


def test_edi_undo_restores_every_follower_and_second_undo_is_noop(tmp_path: Path) -> None:
    # F1: every pre-fit coordinate/e.s.d. is the oracle, not a representative-only sample.
    fitted = _stage_positional_project(tmp_path / 'all-followers')
    before = _coordinate_state(fitted)
    _run(_local_cli(), 'fit', str(fitted), '--verbosity', 'off')
    after_fit = _coordinate_state(fitted)
    assert any(after_fit[name][0] != before[name][0] for name in before), (
        'F1 undo witness must actually move positional coordinates before restoration'
    )
    first = _run(_local_cli(), 'undo', str(fitted))
    restored = _coordinate_state(fitted)
    before_second = _tree_bytes(fitted)
    second = _run(_local_cli(), 'undo', str(fitted))
    assert 'was_no_op=false' in first.stdout, (
        'F1 first edi undo must consume the persisted pre-fit snapshot'
    )
    assert 'was_no_op=true' in second.stdout, (
        'F1 second edi undo must report an exhausted pre-fit snapshot'
    )
    assert _tree_bytes(fitted) == before_second, (
        'F1 second edi undo must preserve every saved project byte'
    )
    mismatches = {
        name: (expected, restored[name])
        for name, expected in before.items()
        if restored[name] != pytest.approx(expected)
    }
    assert not mismatches, (
        'F1 edi undo must restore all follower coordinates and uncertainties: ' + str(mismatches)
    )


def _record_without_informational_fields(text: str) -> str:
    return '\n'.join(
        line
        for line in text.splitlines()
        if line != 'cutoff_policy=off'
        and not line.startswith('elapsed_ms=')
        and not (line.startswith('iter.') and '.elapsed_ms=' in line)
    )


def _axis_state(project_dir: Path) -> dict[str, tuple[float, float | None, bool]]:
    site = _site(project_dir, 'Al1')
    return {
        axis: (parameter.value, parameter.uncertainty, parameter.free)
        for axis in ('fract_x', 'fract_y', 'fract_z')
        for parameter in (getattr(site, axis),)
    }


def _assert_edi_axis_snapshot_roundtrip(tmp_path: Path, kinds: tuple[str, ...]) -> None:
    # Oracle: pre-fit state (a round-trip invariant), plus the independent bracket semantics.
    # Edi's fixed parameters default to engaged zero; capture their presence rather than
    # borrowing crysta's absent default or deriving an oracle from either fitted output.
    suffixes = {'fixed': '', 'absent': '()', 'zero': '(0)', 'positive': '(10)'}
    uncertainties = {'fixed': None, 'absent': None, 'zero': 0.0, 'positive': 0.00010}
    fitted = _stage_positional_project(tmp_path / 'axis-priors')
    structure_file = fitted / 'structures/ncaf.edi'
    structure = structure_file.read_text(encoding='utf-8')
    original = 'Al1 Al 0.25193(10) 0.25193 0.25193 a 8'
    assert structure.count(original) == 1, (
        'F1 prior-state witness must replace exactly the declared tied Al1 site'
    )
    tokens = ' '.join('0.25193' + suffixes[kind] for kind in kinds)
    structure_file.write_text(
        structure.replace(original, f'Al1 Al {tokens} a 8'), encoding='utf-8'
    )
    with (
        pytest.warns(UserWarning, match='crysta.domain.dependent_free_ignored')
        if any(kind != 'fixed' for kind in kinds[1:])
        else contextlib.nullcontext()
    ):
        before = _axis_state(fitted)
    for axis, kind in zip(before, kinds, strict=True):
        assert before[axis][0] == 0.25193 and before[axis][2] is (
            kind != 'fixed' and axis == 'fract_x'
        ), 'F1 each EDI prior token must load its exact declared value and free flag'
        if kind != 'fixed':
            assert before[axis][1] == uncertainties[kind], (
                'F1/F2 each free-axis bracket must retain its declared optional uncertainty'
            )
    LIB.Project.load(fitted).save()
    before = _axis_state(fitted)
    record = _run(
        _local_cli(), 'fit', str(fitted), '--verbosity', 'full', '--report', 'machine'
    ).stdout
    after_fit = _axis_state(fitted)
    assert any(after_fit[axis][0] != before[axis][0] for axis in before) is before['fract_x'][2], (
        'only a free independent x leader may move the tied coordinate during fitting'
    )
    assert all(after_fit[axis][2] is before[axis][2] for axis in before), (
        'F1 fitting and saving must preserve each tied axis free flag'
    )
    snapshot_ids = _fit_snapshot_ids(fitted)
    assert len(snapshot_ids) == len(set(snapshot_ids)) == _machine_number(record, 'n_free'), (
        'F1 persisted snapshot must contain exactly one unique row per fitted basic'
    )
    assert sum(name.startswith('structure.Al1.fract_') for name in snapshot_ids) == int(
        before['fract_x'][2]
    ), 'F1 the tied Al1 basic must occupy one snapshot row rather than its axis count'
    first = _run(_local_cli(), 'undo', str(fitted))
    restored = _axis_state(fitted)
    before_second = _tree_bytes(fitted)
    second = _run(_local_cli(), 'undo', str(fitted))
    assert 'was_no_op=false' in first.stdout, (
        'F1 first edi undo must consume the saved tied-axis snapshot'
    )
    assert 'was_no_op=true' in second.stdout, (
        'F1 second edi undo must report an exhausted tied-axis snapshot'
    )
    assert _tree_bytes(fitted) == before_second, (
        'F1 second edi undo must preserve every saved project byte'
    )
    assert restored == before, (
        'F1/F2 edi save/load/undo must recover every tied axis value, optional uncertainty, '
        f'and free flag exactly: {kinds}: {restored}'
    )


def test_edi_nonfirst_free_axis_prior_survives_saved_undo(tmp_path: Path) -> None:
    _assert_edi_axis_snapshot_roundtrip(tmp_path, ('fixed', 'positive', 'fixed'))


# Same independently enumerated input-contract matrix as crysta: fixed tokens have
# absent uncertainty; tied free axes must agree on numeric seed e.s.d., with absent
# and engaged zero both seeding zero. Every nonempty free subset is represented.
_AXIS_PRIOR_ARRANGEMENTS = [
    kinds
    for kinds in product(('fixed', 'absent', 'zero', 'positive'), repeat=3)
    if kinds != ('fixed', 'fixed', 'fixed')
    and not ('positive' in kinds and any(kind in {'absent', 'zero'} for kind in kinds))
]


@pytest.mark.parametrize(
    'kinds', _AXIS_PRIOR_ARRANGEMENTS, ids=['-'.join(kinds) for kinds in _AXIS_PRIOR_ARRANGEMENTS]
)
def test_edi_all_accepted_axis_prior_arrangements_survive_saved_undo(
    tmp_path: Path, kinds: tuple[str, ...]
) -> None:
    _assert_edi_axis_snapshot_roundtrip(tmp_path, kinds)


@pytest.mark.parametrize(
    'kinds',
    [('absent', 'zero', 'fixed'), ('zero', 'absent', 'fixed')],
    ids=['absent-zero-fixed', 'zero-absent-fixed'],
)
def test_edi_mixed_optional_axis_priors_survive_saved_undo(
    tmp_path: Path, kinds: tuple[str, ...]
) -> None:
    _assert_edi_axis_snapshot_roundtrip(tmp_path, kinds)


def test_both_cli_surfaces_save_byte_equal_trees_and_conforming_records(
    tmp_path: Path,
) -> None:
    crysta_project = _stage_project(tmp_path / 'crysta-project')
    edi_project = _stage_project(tmp_path / 'edi-project')
    source_record = (crysta_project / 'project.edi').read_bytes()
    assert (edi_project / 'project.edi').read_bytes() == source_record, (
        'both CLI persistence surfaces must begin from the same committed partial record'
    )
    crysta_result = _run(
        [str(_crysta_cli())],
        'fit',
        str(crysta_project),
        '--verbosity',
        'full',
    )
    edi_result = _run(
        [sys.executable, '-m', 'edi'],
        'fit',
        str(edi_project),
        '--report',
        'machine',
        '--verbosity',
        'full',
    )

    crysta_tree, crysta_record = project_tree_parts(crysta_project, normalize_fit_time=True)
    edi_tree, edi_record = project_tree_parts(edi_project, normalize_fit_time=True)
    assert crysta_tree == edi_tree, (
        'the same starting project fitted by either CLI must leave every non-record project '
        'path and byte equal except the positive wall-clock fit duration'
    )
    expected_carried = source_record.replace(b'_edi.schema_version 2', b'_edi.schema_version 3', 1)
    assert crysta_record == expected_carried, (
        'the disengaged crysta CLI must preserve the partial project record apart from schema '
        'reconciliation'
    )
    assert (
        project_record_without_fields(edi_record, 'created', 'last_modified', 'timestamp')
        == crysta_record
    ), (
        'edi persistence must add only the three absent owned metadata fields to the carried '
        'record, rather than accepting the current record as a new golden'
    )
    assert project_record_value(edi_record, 'timestamp') == b'?', (
        'edi persistence must spell the loaded empty timestamp as the STAR sentinel'
    )
    assert project_record_datetime(edi_record, 'last_modified') > project_record_datetime(
        edi_record, 'created'
    ), 'edi persistence must materialize its owned dates and advance last_modified on save'
    assert _record_without_informational_fields(
        crysta_result.stdout
    ) == _record_without_informational_fields(edi_result.stdout), (
        'machine reports must diff clean after removing the established timing-only field and '
        'crysta-only cutoff-policy provenance'
    )


_RESULT_AXIS_ARRANGEMENTS = [
    *[
        tuple('positive' if free else 'fixed' for free in flags)
        for flags in product((False, True), repeat=3)
        if any(flags)
    ],
    ('absent', 'zero', 'fixed'),
    ('zero', 'absent', 'fixed'),
]


def _stage_result_axes(destination: Path, tokens: tuple[str, ...]) -> Path:
    staged = _stage_positional_project(destination)
    path = staged / 'structures/ncaf.edi'
    text = path.read_text(encoding='utf-8')
    original = 'Al1 Al 0.25193(10) 0.25193 0.25193 a 8'
    assert text.count(original) == 1, 'the result witness must replace exactly the tied Al1 site'
    path.write_text(text.replace(original, f'Al1 Al {" ".join(tokens)} a 8'), encoding='utf-8')
    return staged


@pytest.mark.parametrize('mode', ['memory', 'saved', 'crysta-calc'])
@pytest.mark.parametrize(
    'kinds',
    _RESULT_AXIS_ARRANGEMENTS,
    ids=['-'.join(kinds) for kinds in _RESULT_AXIS_ARRANGEMENTS],
)
def test_edi_tied_result_uncertainty_reaches_every_free_axis(
    tmp_path: Path, mode: str, kinds: tuple[str, ...]
) -> None:
    # Review-10 F1: agreement between the returned result, the model and both consumers is
    # a representation invariant. An old companion e.s.d. is not a fitted-result oracle.
    suffixes = {'fixed': '', 'positive': '(10)', 'absent': '()', 'zero': '(0)'}
    staged = _stage_result_axes(
        tmp_path / 'input', tuple('0.25193' + suffixes[kind] for kind in kinds)
    )
    project = LIB.Project.load(staged)
    project.save()
    before = _axis_state(staged)
    project = LIB.Project.load(staged)
    result = project.fit_joint()
    keys = [key for key in result.uncertainty if 'Al1' in key and '.fract_' in key]
    assert len(keys) == int(before['fract_x'][2]), (
        'the returned result may name a tied basic only when its independent x is free'
    )
    expected = float(result.uncertainty[keys[0]]) if keys else before['fract_x'][1]
    record = LIB.machine_report(project, result, LIB.VerbosityEnum.FULL)
    if keys:
        reported = _machine_number(record, 'param.Al1.fract_x.uncertainty')
        assert reported == pytest.approx(expected, rel=1e-9, abs=1e-15), (
            'the returned uncertainty and machine record must represent the same independent basic'
        )
    else:
        assert 'param.Al1.fract_x.uncertainty=' not in record, (
            'an ignored follower flag must never appear as a solved uncertainty column'
        )
    assert all(expected != before[axis][1] for axis in before if before[axis][2]), (
        'F1 every free-axis seed must differ from the fitted uncertainty in this witness'
    )
    if mode != 'memory':
        saved = tmp_path / 'saved'
        project.save_as(saved)
        if mode == 'crysta-calc':
            # The other product must consume and re-save the fitted result unchanged during
            # a forward calculation, not replace it by performing another optimization.
            _run([str(_crysta_cli())], str(saved), 'calc')
        project = LIB.Project.load(saved)
    site = next(item for item in project.structure.atom_sites if item.id == 'Al1')
    for axis, prior in before.items():
        parameter = getattr(site, axis)
        assert parameter.free is prior[2], 'F1 result landing must retain declared free flags'
        if prior[2] or (mode == 'memory' and keys):
            assert parameter.uncertainty == pytest.approx(expected, rel=1e-9, abs=1e-15), (
                f'F1 {mode} must carry the fitted uncertainty on every declared-free tied axis: '
                f'{axis}, {kinds}, expected {expected}, got {parameter.uncertainty}'
            )
        else:
            assert parameter.uncertainty == prior[1], (
                'F1 a fixed companion must retain its own uncertainty state'
            )


@pytest.mark.parametrize(
    'tokens',
    [
        ('0.25193(10)', '0.25193(20)', '0.25193(10)'),
        ('0.25193()', '0.25193(10)', '0.25193()'),
    ],
    ids=['conflicting-positive', 'absent-versus-positive'],
)
def test_edi_first_fit_refuses_conflicting_tied_uncertainties(
    tmp_path: Path, tokens: tuple[str, ...]
) -> None:
    staged = _stage_result_axes(tmp_path / 'conflict', tokens)
    before = _tree_bytes(staged)
    arguments = ['fit', str(staged), '--verbosity', 'off', '--dry']
    engine = subprocess.run(
        [str(_crysta_cli()), *arguments], capture_output=True, text=True, check=False, timeout=30
    )
    assert engine.returncode == 0 and 'dependent_free_ignored' in engine.stderr, (
        'the engine must warn and ignore conflicting follower flags while retaining the x leader'
    )
    edi = subprocess.run(
        [*_local_cli(), *arguments], capture_output=True, text=True, check=False, timeout=30
    )
    assert edi.returncode == 0 and 'dependent_free_ignored' in edi.stderr, (
        'edi must warn and ignore conflicting follower flags without redirecting their leader'
    )
    assert _tree_bytes(staged) == before, 'a refused fit must not change the input project'
