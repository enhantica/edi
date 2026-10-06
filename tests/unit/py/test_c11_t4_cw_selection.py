"""public-contract gates for CW experiment selection and fitless plumbing."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import edi
from e04_t5_calculator_bytes import without_calculator

from conftest import project_record_datetime, tree_bytes_with_normalized_project_metadata

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / 'tests/fixtures/c11_t4_cw_selection'
ABSORPTION_FIXTURE = ROOT / 'tests/fixtures/c09_t6_ncaf_5bank_absorption'
CASES = FIXTURE / 'cases'
MANIFEST = FIXTURE / 'manifest.json'
CW_FIELDS = (
    'peak.broad_gauss_u',
    'peak.broad_gauss_v',
    'peak.broad_gauss_w',
    'peak.broad_lorentz_x',
    'peak.broad_lorentz_y',
    'instrument.setup_wavelength',
    'instrument.calib_twotheta_offset',
)


def _manifest() -> dict[str, Any]:
    return json.loads(MANIFEST.read_text(encoding='utf-8'))


def _project_for_case(tmp_path: Path, case: str) -> Path:
    project = tmp_path / case
    (project / 'structures').mkdir(parents=True)
    (project / 'experiments').mkdir()
    shutil.copy2(FIXTURE / 'structure.edi', project / 'structures/ncaf.edi')
    shutil.copy2(CASES / f'{case}.edi', project / 'experiments/wish_5_6.edi')
    return project


def _classification(tmp_path: Path, case: str) -> tuple[bool, str]:
    try:
        edi.Project.load(_project_for_case(tmp_path, case))
    except edi.IoError as error:
        return False, str(error)
    return True, ''


def _tree_bytes(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob('*'))
        if path.is_file()
    }


def _assert_fixed(parameter: Any, where: str) -> None:
    assert parameter.free is False, f'{where} unexpectedly became free in fitless '


def _get_experiment_field(experiment: Any, path: str) -> Any:
    category, name = path.split('.', maxsplit=1)
    return getattr(getattr(experiment, category), name)


def _set_experiment_field(experiment: Any, path: str, value: Any) -> None:
    category, name = path.split('.', maxsplit=1)
    setattr(getattr(experiment, category), name, value)


def _rewrite_experiment(project: Path, replacements: dict[str, str]) -> None:
    path = project / 'experiments/wish_5_6.edi'
    text = path.read_text(encoding='utf-8')
    for before, after in replacements.items():
        assert text.count(before) == 1, f'fixture seam is not unique: {before!r}'
        text = text.replace(before, after)
    path.write_text(text, encoding='utf-8')


def _run_isolated(script: str, *arguments: Path) -> dict[str, Any]:
    completed = subprocess.run(
        [sys.executable, '-c', script, *(str(argument) for argument in arguments)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 0, (
        f'isolated public-API probe crashed or escaped its structured boundary '
        f'(rc={completed.returncode}): {completed.stderr}'
    )
    assert completed.stdout.strip(), 'isolated public-API probe produced no result'
    return json.loads(completed.stdout)


def test_c11_t4_beam_mode_matrix_defaults_and_quoted_round_trip(tmp_path: Path) -> None:
    """Mirror crysta's b9aee906 matrix, including both historical absence defaults."""
    cases = {
        name: expected
        for name, expected in _manifest()['classifications'].items()
        if name
        in {
            'cwl_valid',
            'tof_valid',
            'cwl_with_tof_beam',
            'tof_with_cwl_beam',
            'cwl_bad_beam_hyphen',
            'cwl_no_beam',
            'tof_no_peak',
        }
    }
    #  retires the FCJ/BeBa reservations recorded by the historical oracle.
    cases.update(cwl_reserved_fcj=True, cwl_reserved_beba=True)
    observed = {case: _classification(tmp_path / 'classifications', case)[0] for case in cases}
    assert observed == cases, ' selector matrix retains all crossings and completes FCJ/BeBa'

    source = _project_for_case(tmp_path / 'round-trip-source', 'cwl_valid')
    project = edi.Project.load(source)
    destination = tmp_path / 'round-trip-destination'
    project.save_as(destination)
    experiment_text = (destination / 'experiments/wish_5_6.edi').read_text(encoding='utf-8')
    assert '_experiment_type.beam_mode "constant wavelength"\n' in experiment_text

    source_lines = (CASES / 'cwl_valid.edi').read_text(encoding='utf-8').splitlines()
    saved_lines = experiment_text.splitlines()
    dictionary_tags = {
        tag for tags in _manifest()['dictionary']['families'].values() for tag in tags
    }
    source_tag_lines = {
        line.split(maxsplit=1)[0]: line
        for line in source_lines
        if line.startswith(tuple(dictionary_tags))
    }
    saved_tag_lines = {
        line.split(maxsplit=1)[0]: line
        for line in saved_lines
        if line.startswith(tuple(dictionary_tags))
    }
    assert saved_tag_lines == source_tag_lines


def test_c11_t57_formerly_reserved_cw_rungs_load_and_unknown_still_refuses(tmp_path: Path) -> None:
    """completes the historical FCJ/BeBa tokens on the existing selector seam."""
    for case in ('cwl_reserved_fcj', 'cwl_reserved_beba'):
        accepted, message = _classification(tmp_path / case, case)
        assert accepted, ' formerly reserved CW profile must load: ' + message

    accepted, unknown_message = _classification(tmp_path / 'unknown', 'cwl_unknown_peak')
    assert accepted is False, ' unknown profile tokens must remain rejected'
    assert 'cwl-not-a-profile' in unknown_message, ' unknown-token diagnostic names the token'
    assert 'unknown' in unknown_message.lower(), (
        ' unknown tokens remain distinct from completed reservations'
    )


def test_c11_t4_forbidden_family_tags_name_selector_and_crossing_tag(
    tmp_path: Path,
) -> None:
    """A family crossing is diagnostic at edi's boundary, not deferred to crysta."""
    crossings = {
        'cwl_with_tof_tag': (
            'cwl-tch-pseudo-voigt',
            '_instrument.calib_d_to_tof_linear',
        ),
        'tof_with_cw_tag': (
            'tof-jorgensen',
            '_instrument.setup_wavelength',
        ),
    }
    for case, (peak_type, crossing_tag) in crossings.items():
        accepted, message = _classification(tmp_path / case, case)
        assert accepted is False
        assert '_peak.type' in message
        assert peak_type in message
        assert crossing_tag in message


def test_c11_t4_two_theta_and_measured_values_round_trip_non_trivially(tmp_path: Path) -> None:
    """The CW axis and measured columns survive parse/write/reload as a round-trip invariant."""
    source = _project_for_case(tmp_path / 'data-source', 'cwl_valid')
    rows = (
        ('18.25 1 0 1\n', '18.25 1 101.125 0.75\n'),
        ('31.613267 2 0 1\n', '31.613267 2 -2.5 1.25\n'),
        ('39.5 3 0 1\n', '39.5 3 303.875 2.5\n'),
    )
    _rewrite_experiment(source, dict(rows))
    expected_grid = [18.25, 31.613267, 39.5, 72.125, 110.75, 150.5]
    expected_observed = [101.125, -2.5, 303.875, 0.0, 0.0, 0.0]
    expected_sigma = [0.75, 1.25, 2.5, 1.0, 1.0, 1.0]

    loaded = edi.Project.load(source)
    assert loaded.experiment.data is not None
    assert list(loaded.experiment.data.two_theta) == expected_grid
    assert list(loaded.experiment.data.intensity_meas) == expected_observed
    assert list(loaded.experiment.data.intensity_meas_su) == expected_sigma

    destination = tmp_path / 'data-round-trip'
    loaded.save_as(destination)
    saved = (destination / 'experiments/wish_5_6.edi').read_text(encoding='utf-8')
    assert '\n_data.two_theta\n_data.id\n_data.intensity_meas\n_data.intensity_meas_su\n' in saved
    restored = edi.Project.load(destination)
    assert restored.experiment.data is not None
    assert list(restored.experiment.data.two_theta) == expected_grid
    assert list(restored.experiment.data.intensity_meas) == expected_observed
    assert list(restored.experiment.data.intensity_meas_su) == expected_sigma


def test_c11_t4_existing_tof_writer_goldens_remain_byte_exact(tmp_path: Path) -> None:
    """Regression pins only: two surviving presence shapes have canonical schema-3 bytes.

    Their ADP-type columns are transcribed from the source projects, not regenerated from the
    writer under test. 's declared fourth TOF calibration term forces the sole new
    canonical writer row in each pin.
    """
    #  retires the old schema-1 byte freeze (its purpose died with the mandatory epoch).
    # The successor keeps the useful claim: absent/present profile and absorption shapes serialize
    # deterministically, now against the reviewed schema-3 canonical fixtures.
    c09 = ABSORPTION_FIXTURE
    cases = (
        (
            c09 / 'key_absent_project',
            c09 / 'expected/desired_writer/key_absent',
        ),
        (
            c09 / 'expected/desired_writer/type_none',
            c09 / 'expected/desired_writer/type_none',
        ),
    )
    assert all(source.is_dir() and golden.is_dir() for source, golden in cases)
    for index, (source, golden) in enumerate(cases):
        destination = tmp_path / f'tof-{index}'
        edi.Project.load(source).save_as(destination)
        actual = _tree_bytes(destination)
        record = actual.pop('project.edi', None)
        assert record is not None, (
            'the canonical TOF writer tree must add the required project.edi identity record'
        )
        actual = {name: without_calculator(name, data) for name, data in actual.items()}
        assert actual == _tree_bytes(golden), (
            'adding project identity must leave every pre-existing canonical TOF golden path '
            'and byte unchanged apart from the checked  calculator block'
        )
        normalized = tree_bytes_with_normalized_project_metadata(
            destination, 'created', 'last_modified'
        )['project.edi'].decode()
        assert re.fullmatch(
            r'_edi\.schema_version 3\n\n'
            r'_metadata\.name +untitled_project\n'
            r'_metadata\.title +"Untitled Project"\n'
            r'_metadata\.description +\?\n'
            r'_metadata\.created +<NORMALIZED-WALL-CLOCK>\n'
            r'_metadata\.last_modified +<NORMALIZED-WALL-CLOCK>\n'
            r'_metadata\.timestamp +\?\n',
            normalized,
        ), (
            'the new TOF golden artifact must be exactly the schema-3 default identity record; '
            'only its two independently generated wall-clock values are variable'
        )
        assert project_record_datetime(record, 'last_modified') > project_record_datetime(
            record, 'created'
        ), (
            'the new TOF identity record must carry materializable dates and a strictly advanced '
            'successful-save time'
        )
