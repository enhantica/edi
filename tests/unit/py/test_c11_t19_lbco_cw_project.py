"""fork-independent gates for the LBCO/HRPT CW project example."""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Any

import edi
import pytest

from conftest import corpus_case_dir
from tests.model_calculation import calculate_on_grid

ROOT = Path(__file__).resolve().parents[3]
EXAMPLES = ROOT / 'examples'
MEASUREMENT = ROOT / 'knowledge/verification/fullprof/pd-neut-cwl_lbco-hrpt_basic/lbco.dat'
CW_FIXTURE = ROOT / 'tests/fixtures/c11_t4_cw_selection'

COMMON_FREE_PATHS = {
    'structure.cell.length_a',
    'experiment.instrument.calib_twotheta_offset',
    'experiment.linked_structure.scale',
    *(f'experiment.background[{index}].intensity' for index in range(5)),
}
SHAPE_B_FREE_PATHS = {
    *COMMON_FREE_PATHS,
    *(f'structure.atom_sites[{label}].adp_iso' for label in ('La', 'Ba', 'Co', 'O')),
    *(
        f'experiment.peak.{name}'
        for name in (
            'broad_gauss_u',
            'broad_gauss_v',
            'broad_gauss_w',
            'broad_lorentz_y',
        )
    ),
}


def _project_path() -> Path:
    path = corpus_case_dir('lbco-hrpt-s2') / 'project'
    assert path.is_dir(), 'expected the LBCO/HRPT project in its ruled crysta corpus home'
    structures = sorted((path / 'structures').glob('*.edi'))
    experiments = sorted((path / 'experiments').glob('*.edi'))
    analyses = sorted((path / 'analysis').glob('*.edi'))
    assert structures and experiments and analyses, (
        f'{path}: parent project must retain structures/, experiments/, and analysis/ EDIs'
    )
    structure_text = '\n'.join(item.read_text(encoding='utf-8') for item in structures)
    experiment_text = '\n'.join(item.read_text(encoding='utf-8') for item in experiments)
    assert (
        '_peak.type cwl-tch-pseudo-voigt' in experiment_text
        and '_instrument.setup_wavelength 1.494' in experiment_text
        and all(
            re.search(rf'^\s*{label}\s+{label}\s+', structure_text, re.MULTILINE)
            for label in ('La', 'Ba', 'Co', 'O')
        )
    ), f'{path}: the named parent no longer has the committed LBCO/HRPT fingerprint'
    return path


def _load(path: Path | None = None) -> Any:
    return edi.Project.load(path or _project_path())


def _free_paths(project: Any) -> set[str]:
    parameters: dict[str, Any] = {
        'structure.cell.length_a': project.structure.cell.length_a,
        'experiment.instrument.calib_twotheta_offset': (
            project.experiment.instrument.calib_twotheta_offset
        ),
        'experiment.linked_structure.scale': project.experiment.linked_structure.scale,
        'experiment.peak.broad_gauss_u': project.experiment.peak.broad_gauss_u,
        'experiment.peak.broad_gauss_v': project.experiment.peak.broad_gauss_v,
        'experiment.peak.broad_gauss_w': project.experiment.peak.broad_gauss_w,
        'experiment.peak.broad_lorentz_y': project.experiment.peak.broad_lorentz_y,
    }
    parameters.update({
        f'structure.atom_sites[{site.id}].adp_iso': site.adp_iso
        for site in project.structure.atom_sites
    })
    parameters.update({
        f'experiment.background[{index}].intensity': point.intensity
        for index, point in enumerate(project.experiment.background)
    })
    return {path for path, parameter in parameters.items() if parameter.free}


def _measurement_rows() -> list[tuple[float, float, float]]:
    return [
        tuple(float(value) for value in line.split())
        for line in MEASUREMENT.read_text(encoding='utf-8').splitlines()
        if line.strip()
    ]


def _data_rows(project: Any) -> list[tuple[float, float, float]]:
    data = project.experiment.data
    assert data is not None
    return [
        (float(grid), float(observed), float(sigma))
        for grid, observed, sigma in zip(
            data.two_theta,
            data.intensity_meas,
            data.intensity_meas_su,
            strict=True,
        )
    ]


def test_c11_t19_project_loads_complete_with_ruled_free_profile_shape() -> None:
    project = _load()
    assert len(project.experiments) == 1
    data = project.experiment.data
    assert data is not None
    assert len(data.two_theta) == len(data.intensity_meas) == len(data.intensity_meas_su) == 3098
    assert project.experiment.peak.type == edi.PeakProfileTypeEnum.CWL_TCH_PSEUDO_VOIGT, (
        'the CW project must retain its exact peak selector'
    )
    assert float(project.experiment.instrument.setup_wavelength.value) == 1.494
    assert _free_paths(project) == SHAPE_B_FREE_PATHS


def test_c11_t19_embedded_loop_is_bit_identical_to_vendored_measurement() -> None:
    expected = _measurement_rows()
    actual = _data_rows(_load())
    assert len(expected) == len(actual) == 3098
    assert actual == expected


def test_c11_t19_claim_reports_but_excludes_reduced_chi_square() -> None:
    project_path = _project_path()
    surfaces = [
        project_path.parent / 'project-README.md',
        ROOT / 'README.md',
        EXAMPLES / 'fit_lbco_hrpt.py',
    ]
    relevant = [
        path.read_text(encoding='utf-8')
        for path in surfaces
        if path.is_file()
        and all(token in path.read_text(encoding='utf-8').lower() for token in ('lbco', 'hrpt'))
    ]
    claim = '\n'.join(relevant)
    assert re.search(r'reduced\s+(?:chi|χ)', claim, re.IGNORECASE)
    assert re.search(
        r'(?:reduced\s+(?:chi|χ).{0,180}(?:reported|not compared|never compared|excluded))'
        r'|(?:(?:reported|not compared|never compared|excluded).{0,180}reduced\s+(?:chi|χ))',
        claim,
        re.IGNORECASE | re.DOTALL,
    ), 'the LBCO/HRPT claim must report reduced chi-square while excluding it from comparison'


def test_c11_t19_declared_nonpositive_caglioti_variance_still_names_uvw(
    tmp_path: Path,
) -> None:
    project_path = tmp_path / 'invalid-declared-model'
    (project_path / 'structures').mkdir(parents=True)
    (project_path / 'experiments').mkdir()
    shutil.copy2(CW_FIXTURE / 'structure.edi', project_path / 'structures/ncaf.edi')
    source = (CW_FIXTURE / 'cases/cwl_valid.edi').read_text(encoding='utf-8')
    for tag, value in (
        ('_peak.broad_gauss_u', '0'),
        ('_peak.broad_gauss_v', '0'),
        ('_peak.broad_gauss_w', '-1'),
    ):
        source = re.sub(rf'^{tag}\s+\S+$', f'{tag} {value}', source, flags=re.MULTILINE)
    (project_path / 'experiments/wish_5_6.edi').write_text(source, encoding='utf-8')

    project = edi.Project.load(project_path)
    with pytest.raises(ValueError, match=r'.+') as raised:
        calculate_on_grid(edi, project)
    message = str(raised.value)
    assert all(tag in message for tag in ('_peak.broad_gauss_u', '/v', '/w'))
