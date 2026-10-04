"""Complete I/O and subprocess controls belong to the integration runtime tier.

: these formerly UNMEASURED controls now complete their passing paths.
The serial measurement exceeded the unit bound; relocation preserves every
function body, assertion, independent input and subprocess boundary.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

import edi

from conftest import project_record_datetime, tree_bytes_with_normalized_project_metadata
from tests.unit.py.test_c09_t6_io_seams import (
    KEY_ABSENT,
    TYPE_NONE,
)
from tests.unit.py.test_c11_t48_cif_metadata_behavior import PROJECT
from tests.unit.py.test_c11_t48_python_surface_necessity import (
    CHECKER,
    _expected_parameters,  # noqa: PLC2701 - reuse the unchanged hidden oracle
    _expected_project_free_flags,  # noqa: PLC2701 - reuse the unchanged hidden oracle
    _load_module,  # noqa: PLC2701 - reuse the unchanged hidden oracle
    _manifest,  # noqa: PLC2701 - reuse the unchanged hidden oracle
    _project_path,  # noqa: PLC2701 - reuse the unchanged hidden oracle
)
from tests.unit.py.test_c12_t3_space_group_code_wiring import (
    _copy_name_only_project,  # noqa: PLC2701 - reuse the unchanged hidden oracle
    _replace_once,  # noqa: PLC2701 - reuse the unchanged hidden oracle
    _resolved_setting,  # noqa: PLC2701 - reuse the unchanged hidden oracle
)

ROOT = Path(__file__).resolve().parents[3]


def test_c09_t6_absent_and_explicit_none_share_one_canonical_regression_pin(
    tmp_path: Path,
) -> None:
    saved: dict[str, Path] = {}
    for name, source in (('absent', KEY_ABSENT), ('explicit-none', TYPE_NONE)):
        project = edi.Project.load(source)
        experiment = project.experiments[0]
        assert experiment.peak.type == edi.PeakProfileTypeEnum.TOF_JORGENSEN, (
            'the Jorgensen project must retain its exact peak selector'
        )
        assert experiment.absorption.type == 'none', (
            'an absent selector and an explicit none selector must load as the same typed state'
        )
        assert isinstance(experiment.absorption, edi.NoAbsorption), (
            'the normalized none selector must preserve the no-absorption concrete family'
        )
        assert not hasattr(experiment.absorption, 'abscor1'), (
            'the no-absorption concrete type must not expose cylinder-only abscor1'
        )
        assert not hasattr(experiment.absorption, 'abscor2'), (
            'the no-absorption concrete type must not expose cylinder-only abscor2'
        )
        destination = tmp_path / name
        project.save_as(destination)
        experiment_text = next((destination / 'experiments').glob('*.edi')).read_text(
            encoding='utf-8'
        )
        assert experiment_text.count('_absorption.type none') == 1, (
            'canonical save must materialize the normalized none selector exactly once'
        )
        assert '_absorption.abscor1' not in experiment_text, (
            'type none must not serialize the cylinder-only abscor1 parameter'
        )
        assert '_absorption.abscor2' not in experiment_text, (
            'type none must not serialize the cylinder-only abscor2 parameter'
        )
        saved[name] = destination

    # Regression pin: the ruled semantic retires explicit-none versus absent as a distinction.
    # The two independent loads own independent wall clocks; every other path and byte is
    # canonical.
    for destination in saved.values():
        record = (destination / 'project.edi').read_bytes()
        assert project_record_datetime(record, 'last_modified') > project_record_datetime(
            record, 'created'
        ), 'each successful canonical save must advance its independently generated wall clock'
    assert tree_bytes_with_normalized_project_metadata(
        saved['absent'], 'created', 'last_modified'
    ) == tree_bytes_with_normalized_project_metadata(
        saved['explicit-none'], 'created', 'last_modified'
    ), (
        'absent and explicit-none inputs must save to one canonical byte tree except for their '
        'independently generated, validated wall-clock values'
    )


def test_c11_t48_each_successful_project_save_advances_last_modified(tmp_path: Path) -> None:
    project = edi.Project.load(PROJECT)
    constructed = project.metadata.last_modified
    project.save_as(tmp_path / 'saved')
    after_save_as = project.metadata.last_modified
    project.save()
    after_save = project.metadata.last_modified

    assert constructed < after_save_as < after_save, (
        'save_as() and the following save() must each advance last_modified strictly, even within '
        'one STAR-format clock tick'
    )


def test_c11_t48_parameters_and_free_parameters_follow_the_core_field_walk() -> None:
    """The field list in model.hpp and bracket flags in the corpus are independent controls."""
    project_path = _project_path()
    project = edi.Project.load(project_path)
    rows = _expected_parameters(project)
    for node, expected in rows:
        actual = list(node.parameters)
        assert actual == expected, ' I3: parameters must follow the owning core field walk'
        assert all(left is right for left, right in zip(actual, expected, strict=True)), (
            ' I3: parameters must preserve the owning core object identities'
        )
    free_flags = _expected_project_free_flags(project, project_path)
    project_parameters = list(project.parameters)
    assert len(free_flags) == len(project_parameters), (
        ' I3: every project parameter must have one independent EDI bracket flag'
    )
    expected_free = [
        parameter
        for parameter, is_free in zip(project_parameters, free_flags, strict=True)
        if is_free
    ]
    actual_free = list(project.free_parameters)
    assert actual_free == expected_free, (
        ' I3: project free parameters must follow independent EDI bracket flags'
    )
    assert all(left is right for left, right in zip(actual_free, expected_free, strict=True)), (
        ' I3: project free parameters must preserve their core object identities'
    )


def test_c11_t48_checker_prints_the_necessity_limit_on_green_and_red(
    tmp_path: Path,
) -> None:
    assert CHECKER.is_file(), ' must provide edi tools/checks/python_surface.py'
    checker = _load_module('c11_t48_edi_python_surface_checker', CHECKER)
    limit = checker.NECESSITY_LIMIT
    assert 'do not prove that a member is needed' in limit, (
        ' I12: the checker must state its necessity-proof limit'
    )

    green = subprocess.run(
        [sys.executable, str(CHECKER), '--check'],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert green.returncode == 0, (
        ' I7: the committed edi checker must pass\n' + green.stdout + green.stderr
    )
    assert limit in green.stdout + green.stderr, (
        ' I12: green checker output must state the necessity-proof limit'
    )

    staged = tmp_path / 'repo'
    staged_checker = staged / 'tools/checks/python_surface.py'
    staged_checker.parent.mkdir(parents=True)
    shutil.copy2(CHECKER, staged_checker)
    staged_manifest = staged / 'data/python-surface.json'
    staged_manifest.parent.mkdir(parents=True)
    manifest = _manifest()
    name = next(
        name for name in sorted(manifest['classification']['module']) if not name.startswith('_')
    )
    manifest['classification']['module'][name]['need'] = {
        'verdict': 'undecided',
        'question': 'red-output control',
    }
    staged_manifest.write_text(json.dumps(manifest), encoding='utf-8')
    red = subprocess.run(
        [sys.executable, str(staged_checker), '--check'],
        cwd=staged,
        capture_output=True,
        text=True,
        check=False,
    )
    assert red.returncode != 0, ' I12: an undecided necessity control must fail the checker'
    assert limit in red.stdout + red.stderr, (
        ' I12: red checker output must state the necessity-proof limit'
    )


def test_e09_t58_delegated_save_persists_crysta_resolved_identity(
    tmp_path: Path,
) -> None:
    source = tmp_path / 'source'
    structure_file = _copy_name_only_project(source)
    _replace_once(
        structure_file,
        '_space_group.name_h_m "I 21 3"',
        '_space_group.name_h_m "  I   21    3  "',
    )
    source_text = structure_file.read_text(encoding='utf-8')
    assert '_space_group.coord_system_code' not in source_text, (
        'the resolved-identity gate requires a source that declares no coordinate-system code'
    )
    assert '_space_group.it_number' not in source_text, (
        'the resolved-identity gate requires a source that declares no IT number'
    )
    expected = _resolved_setting(199, '1')

    project = edi.Project.load(source)
    identity = project.structure.space_group
    assert (identity.it_number, identity.coord_system_code, identity.name_h_m) == (
        None,
        '',
        '  I   21    3  ',
    ), (
        'load must preserve the source identity; resolving and canonicalizing it belongs to the '
        'delegated crysta save path'
    )

    destination = tmp_path / 'saved'
    project.save_as(destination)
    written = (destination / 'structures/ncaf.edi').read_text(encoding='utf-8')
    assert f'_space_group.it_number {expected["it_number"]}\n' in written, (
        "the delegated crysta writer must persist crysta's independently resolved IT number"
    )
    assert f'_space_group.coord_system_code {expected["code"]}\n' in written, (
        'the delegated crysta writer must persist the independently resolved '
        'coordinate-system code'
    )
    assert f'_space_group.name_h_m "{expected["hm_full"]}"\n' in written, (
        'the delegated crysta writer must persist the resolved canonical Hermann-Mauguin spelling'
    )
    restored = edi.Project.load(destination).structure.space_group
    assert (restored.it_number, restored.coord_system_code, restored.name_h_m) == (
        expected['it_number'],
        expected['code'],
        expected['hm_full'],
    ), 'all three resolved identity fields must survive the save-load round trip'


def test_e09_t55_edi_python_fail_under_control(tmp_path: Path) -> None:
    pyproject = tomllib.loads((ROOT / 'pyproject.toml').read_text(encoding='utf-8'))
    assert pyproject['tool']['coverage']['report']['fail_under'] == 80, (
        'the Python report threshold must remain eighty percent'
    )
    sample = tmp_path / 'sample.py'
    sample.write_text(
        'def uncovered():\n    return 1\n\nexecuted = 1\n',
        encoding='utf-8',
    )
    data_file = tmp_path / '.coverage'
    control = subprocess.run(
        [
            sys.executable,
            '-c',
            (
                'from coverage import Coverage\n'
                'from coverage.cmdline import main\n'
                f'path = {str(sample)!r}\n'
                f'rcfile = {str(ROOT / "pyproject.toml")!r}\n'
                f'data_file = {str(data_file)!r}\n'
                f'source = {str(tmp_path)!r}\n'
                'cov = Coverage(config_file=rcfile, data_file=data_file, source=[source])\n'
                'cov.start()\n'
                "exec(compile(open(path, encoding='utf-8').read(), path, 'exec'), {})\n"
                'cov.stop()\n'
                'cov.save()\n'
                "raise SystemExit(main(['report', '--rcfile', rcfile, "
                "'--data-file', data_file]))\n"
            ),
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )
    assert control.returncode != 0, (
        'the seeded below-eighty Python sample must trip fail_under: '
        + control.stdout
        + control.stderr
    )
