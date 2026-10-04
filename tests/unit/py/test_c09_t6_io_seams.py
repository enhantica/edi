"""gates for JvD, absorption, and total bank-name I/O seams."""

from __future__ import annotations

import shutil
from pathlib import Path

import edi
import pytest

from conftest import corpus_case_dir

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / 'tests/fixtures/c09_t6_ncaf_5bank_absorption'
PROJECT = corpus_case_dir('ncaf-wish-3bank-s5') / 'project'
KEY_ABSENT = FIXTURE / 'key_absent_project'
TYPE_NONE = FIXTURE / 'type_none_project'
LORENTZ_TAGS = (
    '_peak.broad_lorentz_gamma_0',
    '_peak.broad_lorentz_gamma_1',
    '_peak.broad_lorentz_gamma_2',
    '_peak.broad_lorentz_size',
    '_peak.broad_lorentz_strain',
)


def _triplet(parameter: object) -> tuple[float, float, bool]:
    return (float(parameter.value), float(parameter.uncertainty), bool(parameter.free))


def _tree_bytes(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob('*'))
        if path.is_file()
    }


def _copy_with_replacement(
    tmp_path: Path,
    *,
    source: Path = PROJECT,
    experiment: str = 'wish_2_9',
    old: str,
    new: str,
) -> Path:
    destination = tmp_path / 'project'
    shutil.copytree(source, destination)
    path = destination / 'experiments' / f'{experiment}.edi'
    text = path.read_text(encoding='utf-8')
    assert text.count(old) == 1
    path.write_text(text.replace(old, new), encoding='utf-8')
    return destination


def test_c09_t6_jvd_and_absorption_load_with_nontrivial_parameter_states() -> None:
    project = edi.Project.load(PROJECT)
    assert [experiment.name for experiment in project.experiments] == [
        'wish_2_9',
        'wish_4_7',
        'wish_5_6',
    ]
    for experiment in project.experiments:
        assert experiment.peak.type == edi.PeakProfileTypeEnum.TOF_JORGENSEN_VON_DREELE, (
            'the JVD project must retain its exact peak selector'
        )
        assert experiment.absorption.type == 'cylinder'
        assert experiment.absorption.abscor1 is not None
        assert experiment.absorption.abscor2 is not None
        assert _triplet(experiment.absorption.abscor2) == (0.0, 0.0, False)
        for field in (
            'broad_lorentz_gamma_0',
            'broad_lorentz_gamma_1',
            'broad_lorentz_gamma_2',
            'broad_lorentz_size',
            'broad_lorentz_strain',
        ):
            assert getattr(experiment.peak, field) is not None

    wish_2, wish_4, wish_5 = project.experiments
    assert _triplet(wish_2.peak.broad_lorentz_gamma_1) == (
        1.6846,
        pytest.approx(0.001),
        True,
    )
    assert _triplet(wish_4.peak.broad_lorentz_gamma_1) == (0.0, 0.0, False)
    assert _triplet(wish_5.peak.broad_lorentz_gamma_1) == (0.0019, 0.0, False)
    assert all(
        _triplet(experiment.absorption.abscor1) == (0.0, 1.0, True)
        for experiment in project.experiments
    )


@pytest.mark.parametrize('tag', LORENTZ_TAGS)
def test_c09_t6_jvd_requires_each_lorentzian_field(tmp_path: Path, tag: str) -> None:
    source = PROJECT / 'experiments/wish_2_9.edi'
    line = next(
        line
        for line in source.read_text(encoding='utf-8').splitlines()
        if line.startswith(tag + ' ')
    )
    malformed = _copy_with_replacement(tmp_path, old=line + '\n', new='')
    with pytest.raises(edi.IoError) as captured:
        edi.Project.load(malformed)
    assert tag in str(captured.value), (
        'the diagnostic must identify the missing required JvD field'
    )


def test_c09_t6_pure_jorgensen_rejects_mixed_lorentzian_body(tmp_path: Path) -> None:
    source = TYPE_NONE
    malformed = _copy_with_replacement(
        tmp_path,
        source=source,
        experiment='wish_5_6',
        old='_peak.type tof-jorgensen\n',
        new='_peak.broad_lorentz_gamma_0 1.25\n_peak.type tof-jorgensen\n',
    )
    with pytest.raises(edi.IoError, match=r'(?i)(jorgensen|lorentz|mixed|peak)'):
        edi.Project.load(malformed)


def test_c09_t6_unknown_peak_selector_names_registration_contract(tmp_path: Path) -> None:
    malformed = _copy_with_replacement(
        tmp_path,
        experiment='wish_5_6',
        old='_peak.type tof-jorgensen-von-dreele',
        new='_peak.type unknown-profile',
    )
    with pytest.raises(edi.IoError) as captured:
        edi.Project.load(malformed)
    message = str(captured.value)
    assert 'unknown-profile' in message, 'the refusal must name the rejected selector token'
    assert 'registered profile token' in message, (
        'the refusal must explain that accepted selectors come from live registration'
    )


@pytest.mark.parametrize('name', ['wish.bad', 'wish[bad', 'wish]bad'])
def test_c09_t6_reserved_bank_delimiters_fail_before_writer_touch(
    tmp_path: Path,
    name: str,
) -> None:
    project = edi.Project.load(KEY_ABSENT)
    project.experiments[0].name = name
    destination = tmp_path / 'must-not-exist'
    with pytest.raises(edi.IoError, match=r'(?i)(unsafe|reserved|delimiter|name)'):
        project.save_as(destination)
    assert not destination.exists()


def test_c09_t6_nontrivial_prefix_names_remain_distinct_on_round_trip(tmp_path: Path) -> None:
    project = edi.Project.load(KEY_ABSENT)
    second = edi.Project.load(KEY_ABSENT).experiment
    second.name = 'wish_5_60'
    project.experiments.add(second)
    destination = tmp_path / 'saved'
    project.save_as(destination)
    restored = edi.Project.load(destination)
    assert [experiment.name for experiment in restored.experiments] == ['wish_5_6', 'wish_5_60']
