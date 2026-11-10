"""public-contract gates for CW experiment selection and fitless plumbing."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import edi

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
    return json.loads(completed.stdout.splitlines()[-1])


def test_c11_t4_ragged_programmatic_cw_pattern_is_a_structured_io_refusal(
    tmp_path: Path,
) -> None:
    """Publicly writable measured columns fail closed instead of reaching unchecked indexing."""
    source = _project_for_case(tmp_path / 'ragged-source', 'cwl_valid')
    destination = tmp_path / 'ragged-destination'
    result = _run_isolated(
        """
import json
import sys
import edi

loaded = edi.Project.load(sys.argv[1])
experiment = loaded.experiment
experiment.data = edi.PdCwlData(
    two_theta=[18.25, 31.613267, 39.5],
    intensity_meas=[101.125, -2.5],
    intensity_meas_su=[0.75, 1.25, 2.5],
)
project = edi.Project(name='ragged-cw')
project.structure = loaded.structure
project.experiments.clear()
# : transfer the held item after detaching it from its first owner.
# The ragged-data diagnostic assertions below remain unchanged.
loaded.experiments.remove(experiment.name)
project.experiments.add(experiment)
try:
    project.save_as(sys.argv[2])
except edi.IoError as error:
    print(json.dumps({
        'status': 'refused',
        'message': str(error),
        'diagnostics': getattr(error, 'diagnostics', None),
    }))
else:
    print(json.dumps({'status': 'wrote'}))
""",
        source,
        destination,
    )
    assert result['status'] == 'refused'
    assert result['diagnostics']
    assert any(
        word in result['message'].lower()
        for word in ('column', 'length', 'ragged', 'two_theta', 'intensity_meas')
    )
