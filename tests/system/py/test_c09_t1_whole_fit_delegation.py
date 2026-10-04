# ruff: noqa: PLC0415, PT011
# Ported verbatim from the retired hidden fitting-test file ( phase C): the
# body keeps its hidden-tier-authored shape — reshaping it for the visible tier's
# lint would churn what the port must preserve.
"""Hidden  gates: whole-fit fidelity to the pinned crysta CLI object graph."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[3]
OBSERVER_SOURCE = ROOT / 'tests/unit/cpp/c08_t2_native_observer.c'
OBSERVER_HARNESS = ROOT / 'tests/system/py/c09_t1_fit_native_harness.py'


def _ncaf_project() -> Path:
    from conftest import corpus_case_dir

    return corpus_case_dir('si-sepd-s2') / 'project'


def _run(
    command: list[str],
    *,
    cwd: Path,
    environment: dict[str, str] | None = None,
    timeout: int = 600,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    return result


def _build_native_observer(tmp_path: Path) -> tuple[Path, str]:
    compiler = shutil.which('cc')
    assert compiler is not None, 'the native I/O observer requires the pinned C compiler'
    if sys.platform.startswith('linux'):
        library = tmp_path / 'c09_t1_native_observer.so'
        command = [compiler, '-shared', '-fPIC', str(OBSERVER_SOURCE), '-ldl', '-o', str(library)]
        preload_variable = 'LD_PRELOAD'
    elif sys.platform == 'darwin':
        library = tmp_path / 'c09_t1_native_observer.dylib'
        command = [compiler, '-dynamiclib', str(OBSERVER_SOURCE), '-o', str(library)]
        preload_variable = 'DYLD_INSERT_LIBRARIES'
    else:
        raise AssertionError(f'no fail-closed native I/O observer for platform {sys.platform!r}')
    _run(command, cwd=tmp_path)
    return library, preload_variable


def _native_events(
    tmp_path: Path,
    library: Path,
    preload_variable: str,
    *,
    counterfactual: bool,
) -> list[str]:
    log_path = tmp_path / ('counterfactual-native.log' if counterfactual else 'fit-native.log')
    sentinel = tmp_path / 'absolute-native-read-counterfactual'
    sentinel.write_bytes(b'observer must report this absolute native read')
    environment = os.environ.copy()
    environment['EDI_C08_NATIVE_OBSERVER_LOG'] = str(log_path)
    previous_preload = environment.get(preload_variable)
    environment[preload_variable] = (
        str(library) if not previous_preload else os.pathsep.join((str(library), previous_preload))
    )
    if sys.platform == 'darwin':
        environment['DYLD_FORCE_FLAT_NAMESPACE'] = '1'
    #  (F-cheap): the observed fit runs the cheap TOF corpus case; its pattern file is
    # staged from the case's own embedded data (the harness reads a whitespace table).
    import edi

    cheap_project = _cheap_case() / 'project'
    pattern_path = tmp_path / 'cheap-pattern.txt'
    if not pattern_path.is_file():
        grid, observed, _sigma = _cheap_measured(edi.Project.load(cheap_project))
        pattern_path.write_text(
            ''.join(f'{x} {y}\n' for x, y in zip(grid, observed, strict=True)),
            encoding='utf-8',
        )
    _run(
        [
            sys.executable,
            str(OBSERVER_HARNESS),
            str(cheap_project),
            str(pattern_path),
            'counterfactual' if counterfactual else 'fit',
            str(sentinel),
        ],
        cwd=tmp_path,
        environment=environment,
        timeout=120,
    )
    assert log_path.is_file(), 'native observer did not initialise'
    return log_path.read_text(encoding='utf-8').splitlines()


def _cheap_case() -> Path:
    """The cheapest TOF single corpus case ( P1.2b F-cheap) for the fit-paying tests.

    The error-path tests keep the NCAF fixture (they load and refuse — no fit runs); the
    delegation and I/O-invariant subjects are vehicle-generic and each paid one or two full
    4122-point fixture fits, so they run on the cheap case in place.
    """
    from conftest import corpus_case_dir

    return corpus_case_dir('si-sepd-s2')


def _cheap_measured(project: Any) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    data = project.experiments[0].data
    assert data is not None
    return (
        np.asarray(data.axis()),
        np.asarray(data.intensity_meas),
        np.asarray(data.intensity_meas_su),
    )


def _mapping(project: Any) -> dict[str, tuple[str, Any]]:
    sites = {site.id: site for site in project.structure.atom_sites}
    mapped: dict[str, tuple[str, Any]] = {}
    for label, field in (
        ('Ca.fract_x', 'fract_x'),
        ('Al.fract_x', 'fract_x'),
        ('Na.fract_x', 'fract_x'),
        ('F1.fract_x', 'fract_x'),
        ('F1.fract_y', 'fract_y'),
        ('F1.fract_z', 'fract_z'),
        ('F2.fract_x', 'fract_x'),
        ('F2.fract_y', 'fract_y'),
        ('F2.fract_z', 'fract_z'),
        ('F3.fract_x', 'fract_x'),
    ):
        site_name = label.split('.', maxsplit=1)[0]
        path = f'structure.atom_sites[{site_name}].{field}'
        mapped[label] = (path, getattr(sites[site_name], field))
    for site_name in ('Ca', 'Al', 'Na', 'F1', 'F2', 'F3'):
        mapped[f'{site_name}.adp_iso'] = (
            f'structure.atom_sites[{site_name}].adp_iso',
            sites[site_name].adp_iso,
        )
    for label, field in (
        ('scale', 'linked_structure.scale'),
        ('calib_d_to_tof_offset', 'instrument.calib_d_to_tof_offset'),
        ('calib_d_to_tof_linear', 'instrument.calib_d_to_tof_linear'),
        ('broad_gauss_sigma_2', 'peak.broad_gauss_sigma_2'),
        ('rise_alpha_0', 'peak.rise_alpha_0'),
        ('rise_alpha_1', 'peak.rise_alpha_1'),
        ('decay_beta_0', 'peak.decay_beta_0'),
        ('decay_beta_1', 'peak.decay_beta_1'),
    ):
        owner = project.experiment
        parts = field.split('.')
        for part in parts[:-1]:
            owner = getattr(owner, part)
        mapped[label] = (f'experiment.{field}', getattr(owner, parts[-1]))
    for index, point in enumerate(project.experiment.background):
        mapped[f'background[{index}]'] = (
            f'experiment.background[{index}].intensity',
            point.intensity,
        )
    return mapped


_PATH_COMPONENT = re.compile(r'(?P<attribute>[A-Za-z_]\w*)(?:\[(?P<selector>[^\]]+)\])?')


def _resolve_edi_parameter(project: Any, path: str, parameter_type: type) -> Any:
    """Resolve an outcome identity through edi's public model, without engine-label knowledge."""
    current = project
    for component in path.split('.'):
        match = _PATH_COMPONENT.fullmatch(component)
        assert match is not None, f'FitOutcome key is not an edi model path: {path!r}'
        attribute = match.group('attribute')
        assert hasattr(current, attribute), (
            f'FitOutcome key does not resolve through the edi model: {path!r}'
        )
        current = getattr(current, attribute)
        selector = match.group('selector')
        if selector is None:
            continue
        if selector.isdecimal():
            index = int(selector)
            assert index < len(current), f'FitOutcome path index is out of range: {path!r}'
            current = current[index]
            continue
        matches = [entry for entry in current if getattr(entry, 'id', None) == selector]
        assert len(matches) == 1, f'FitOutcome path selector is not unique in edi: {path!r}'
        current = matches[0]
    assert isinstance(current, parameter_type), (
        f'FitOutcome key does not identify an edi Parameter: {path!r}'
    )
    return current


def _forbid_io_or_exec(*_args: object, **_kwargs: object) -> None:
    raise AssertionError('fit path attempted file I/O or subprocess execution')


def test_c09_t1_fit_fails_closed_on_malformed_models() -> None:
    import edi

    for mutate in (
        lambda project: setattr(project.structure.space_group, 'name_h_m', 'not-a-space-group'),
        lambda project: project.structure.atom_sites.clear(),
    ):
        project = edi.Project.load(_ncaf_project())
        mutate(project)
        before = (
            project.experiment.peak.broad_gauss_sigma_2.value,
            project.experiment.peak.broad_gauss_sigma_2.uncertainty,
        )
        with pytest.raises(ValueError) as captured:
            project.fit()
        assert str(captured.value).strip(), (
            ': a fail-closed fit must explain itself with a non-empty ValueError'
        )
        assert (
            project.experiment.peak.broad_gauss_sigma_2.value,
            project.experiment.peak.broad_gauss_sigma_2.uncertainty,
        ) == before, 'a malformed-model refusal must leave the project state unchanged'


def test_c09_t1_fit_fails_closed_on_empty_measured_data() -> None:
    import edi

    project = edi.Project.load(_ncaf_project())
    before = (
        project.experiment.peak.broad_gauss_sigma_2.value,
        project.experiment.peak.broad_gauss_sigma_2.uncertainty,
    )
    data = project.experiment.data
    assert data is not None, 'the empty-data refusal witness must begin with model-owned data'
    project.experiment.data = edi.PdTofData(
        time_of_flight=[], intensity_meas=[], intensity_meas_su=[]
    )
    with pytest.raises(ValueError, match=r'(?i)(empty|measured|data)'):
        project.fit()
    assert (
        project.experiment.peak.broad_gauss_sigma_2.value,
        project.experiment.peak.broad_gauss_sigma_2.uncertainty,
    ) == before, 'an empty-data refusal must leave the project state unchanged'
