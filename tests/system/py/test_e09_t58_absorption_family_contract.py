"""F4: real edi load/save agrees with the installed crysta family contract."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import edi
import numpy as np
import pytest

from conftest import crysta_reference_prefix, crysta_reference_source

ROOT = Path(__file__).resolve().parents[3]


def _absorption_fields(directory: Path) -> list[dict[str, str]]:
    return [
        dict(
            line.split(maxsplit=1)
            for line in file.read_text(encoding='utf-8').splitlines()
            if line.startswith('_absorption.')
        )
        for file in sorted((directory / 'experiments').glob('*.edi'))
    ]


def _calculated_patterns(project: edi.Project) -> list[np.ndarray]:
    project.calculate()
    patterns = [
        np.asarray(experiment.data.intensity_calc, dtype=np.float64).copy()
        for experiment in project.experiments
    ]
    assert patterns and all(pattern.size > 2 for pattern in patterns), (
        'F4 the absorption mutation witness must calculate non-trivial bank patterns'
    )
    return patterns


@pytest.mark.parametrize(
    ('body', 'expected'),
    [
        ('_absorption.type cylinder\n', 0.0),
        ('_absorption.type cylinder\n_absorption.abscor1 0.125\n', 0.125),
        ('_absorption.type cylinder\n_absorption.abscor2 0.375\n', 0.0),
        ('_absorption.type none\n_absorption.abscor1 0.125\n', None),
        ('_absorption.type unknown-family\n', None),
    ],
    ids=['missing', 'first-only', 'second-only', 'none-with-coefficient', 'unknown'],
)
def test_absorption_family_acceptance_and_contents_match_crysta(
    tmp_path: Path, capfd: pytest.CaptureFixture[str], body: str, expected: float | None
) -> None:
    corpus = Path(
        os.environ.get('EDI_CRYSTA_CORPUS_ROOT', str(crysta_reference_source() / 'tests/fitting'))
    )
    source = corpus / 'ncaf-wish-3bank-s5/project'
    original = '_absorption.type cylinder\n_absorption.abscor1 0.0(10)\n'
    for name in ('crysta', 'edi'):
        destination = tmp_path / name
        shutil.copytree(source, destination)
        bounded = (source.parent / 'bounded-analysis/analysis.edi').read_text(encoding='utf-8')
        assert '_minimizer.max_iterations 2' in bounded, (
            'F4 serialization witness must derive its budget from the bounded corpus variant'
        )
        (destination / 'analysis/analysis.edi').write_text(
            bounded.replace('_minimizer.max_iterations 2', '_minimizer.max_iterations 1'),
            encoding='utf-8',
        )
        for file in (destination / 'experiments').glob('*.edi'):
            text = file.read_text(encoding='utf-8')
            assert text.count(original) == 1, (
                'F4 fixture must expose exactly one declared cylinder block per bank'
            )
            file.write_text(text.replace(original, body), encoding='utf-8')
    cli = os.environ.get('E09_T58_CRYSTA_CLI', str(crysta_reference_prefix() / 'bin/crysta'))
    reference = subprocess.run(
        [cli, 'fit', str(tmp_path / 'crysta'), '--verbosity', 'off'],
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    if expected is None:
        assert reference.returncode != 0 and 'absorption' in reference.stderr.lower(), (
            'F4 crysta must reject the independently invalid selector or family body'
        )
        with pytest.raises((ValueError, RuntimeError), match=r'absorption|selector'):
            edi.Project.load(tmp_path / 'edi')
        return
    assert reference.returncode == 0, (
        'F4 crysta must accept and save the valid defaulted cylinder: ' + reference.stderr
    )
    project = edi.Project.load(tmp_path / 'edi')
    diagnostics = capfd.readouterr().err
    if '_absorption.abscor2' in body:
        assert diagnostics.count('_absorption.abscor2 has no effect and is ignored') == 3, (
            'F4 an older ignored coefficient must emit its declared compatibility warning'
        )
    for experiment in project.experiments:
        absorption = experiment.absorption
        assert isinstance(absorption, edi.CylinderHewatAbsorption), (
            'F4 cylinder selection must produce the typed cylinder model family'
        )
        assert absorption.abscor1 is not None and absorption.mu_r is None, (
            'F4 a TOF cylinder must contain its active coefficient and no CW-only coefficient'
        )
        assert not hasattr(absorption, 'abscor2'), (
            'F4 the retired coefficient must not reappear in the live model'
        )
        assert absorption.abscor1.value == pytest.approx(expected), (
            'F4 missing active coefficients default to zero without losing supplied values'
        )
    saved = tmp_path / 'edi-saved'
    project.save_as(saved)
    assert _absorption_fields(saved) == _absorption_fields(tmp_path / 'crysta'), (
        'F4 delegation must preserve the same canonical absorption model contents as crysta'
    )


@pytest.mark.parametrize('mutation', ['factory', 'type-setter'])
def test_switching_a_loaded_cylinder_to_none_clears_calculation_state(
    tmp_path: Path, mutation: str
) -> None:
    # Review-8 F4: use a nonzero coefficient so stale family state has an observable effect.
    corpus = Path(
        os.environ.get('EDI_CRYSTA_CORPUS_ROOT', str(crysta_reference_source() / 'tests/fitting'))
    )
    source = corpus / 'ncaf-wish-3bank-s5/project'
    staged = tmp_path / 'loaded-cylinder'
    shutil.copytree(source, staged)
    original = '_absorption.type cylinder\n_absorption.abscor1 0.0(10)\n'
    nonzero = '_absorption.type cylinder\n_absorption.abscor1 0.125\n'
    for file in sorted((staged / 'experiments').glob('*.edi')):
        text = file.read_text(encoding='utf-8')
        assert text.count(original) == 1, (
            'F4 each loaded witness bank must begin with one declared cylinder coefficient pair'
        )
        file.write_text(text.replace(original, nonzero), encoding='utf-8')

    project = edi.Project.load(staged)
    # Start the exact roundtrip witness at the declared serialized precision.
    canonical = tmp_path / 'canonical-cylinder'
    project.save_as(canonical)
    project = edi.Project.load(canonical)
    cylinder_patterns = _calculated_patterns(project)
    assert all(
        isinstance(experiment.absorption, edi.CylinderHewatAbsorption)
        and float(experiment.absorption.abscor1.value) == pytest.approx(0.125)
        for experiment in project.experiments
    ), 'F4 the mutation witness must load the nonzero cylinder family before switching it'

    for experiment in project.experiments:
        if mutation == 'factory':
            edi.AbsorptionFactory.create('none', experiment)
        else:
            experiment.absorption.type = 'none'

    for experiment in project.experiments:
        absorption = experiment.absorption
        assert isinstance(absorption, edi.NoAbsorption), (
            'F4 each mutation route must select the no-absorption model family'
        )
        assert not hasattr(absorption, 'abscor1') and not hasattr(absorption, 'abscor2'), (
            'F4 no-absorption must expose no cylinder-only parameter'
        )
        assert list(absorption.parameters) == [], (
            'F4 no cylinder parameter may remain held in the selected family parameter walk'
        )

    none_patterns = _calculated_patterns(project)
    assert any(
        not np.array_equal(cylinder, none, equal_nan=True)
        for cylinder, none in zip(cylinder_patterns, none_patterns, strict=True)
    ), 'F4 switching off a nonzero absorption coefficient must change the calculation'

    saved = tmp_path / 'saved-none'
    project.save_as(saved)
    reloaded = edi.Project.load(saved)
    reloaded_patterns = _calculated_patterns(reloaded)
    assert all(
        isinstance(experiment.absorption, edi.NoAbsorption)
        and list(experiment.absorption.parameters) == []
        for experiment in reloaded.experiments
    ), 'F4 save/load must preserve the empty no-absorption family state'
    assert all(
        np.array_equal(before, after, equal_nan=True)
        for before, after in zip(none_patterns, reloaded_patterns, strict=True)
    ), 'F4 a no-absorption calculation must be identical before and after save/load'
