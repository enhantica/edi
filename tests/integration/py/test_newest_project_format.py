"""Older project addresses are rejected; current aliases and slots remain distinct."""

import shutil
from pathlib import Path

import edi as engine
import pytest

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / 'tests/fixtures/loop_parameter_ids'
OLDER = [
    ('line-segment', 'bank.background[0]'),
    ('line-segment', 'bank.background[0].intensity'),
    ('line-segment', 'bank.background.1.intensity'),
    ('polynomial', 'bank.background[0]'),
    ('polynomial', 'bank.background.1.coef'),
    ('chebyshev', 'bank.background.1.coef'),
    ('line-segment', 'bank.scale'),
    ('line-segment', 'bank.march_r'),
    ('line-segment', 'bank.march_random_fract'),
    ('line-segment', 'bank.linked_structure.0.scale'),
    ('line-segment', 'bank.preferred_orientation.0.march_r'),
    ('line-segment', 'bank.preferred_orientation.0.march_random_fract'),
    ('line-segment', 'bank.background[1]'),
    ('polynomial', 'bank.background.2.coef'),
    ('chebyshev', 'bank.background[2]'),
]


@pytest.mark.parametrize(('kind', 'older'), OLDER)
@pytest.mark.parametrize('role', ['alias', 'fit-state'])
def test_older_project_addresses_are_refused_with_their_name(kind, older, role, tmp_path):
    source = tmp_path / 'input'
    shutil.copytree(FIXTURE / kind, source)
    path = source / 'analysis/analysis.edi'
    added = (
        f'loop_\n_alias.id\n_alias.parameter_unique_name\nold {older}\n'
        if role == 'alias'
        else 'loop_\n_fit_parameter.id\n_fit_parameter.start_value\n'
        f'_fit_parameter.start_uncertainty\n{older} 12.5 0.125\n'
    )
    path.write_text(path.read_text() + '\n' + added)
    before = {p.relative_to(source): p.read_bytes() for p in source.rglob('*') if p.is_file()}
    with pytest.raises((ValueError, RuntimeError)) as caught:
        engine.Project.load(source)
    message = str(caught.value)
    assert older in message, (
        'An older project address must be refused with a message naming it and the older version'
    )
    assert 'older' in message.lower(), (
        'The error must explain that the input comes from an older version'
    )
    assert 'version' in message.lower(), (
        'The older-input diagnostic must name its version incompatibility'
    )
    assert len(message) <= 240, (
        'The older-version diagnostic must remain a short load-error message'
    )
    assert len(message.splitlines()) <= 2, (
        'The older-version refusal must not become a multiline traceback'
    )
    assert {
        p.relative_to(source): p.read_bytes() for p in source.rglob('*') if p.is_file()
    } == before, 'A refused older project must leave every supplied file unchanged'


@pytest.mark.parametrize('role', ['alias', 'fit-state'])
def test_current_public_alias_and_compact_slot_keep_their_own_role(role, tmp_path):
    source = tmp_path / 'input'
    shutil.copytree(FIXTURE / 'line-segment', source)
    identity = 'bank.background.pA.intensity' if role == 'alias' else 'bank.background.pA'
    path = source / 'analysis/analysis.edi'
    added = (
        f'loop_\n_alias.id\n_alias.parameter_unique_name\ncurrent {identity}\n'
        if role == 'alias'
        else 'loop_\n_fit_parameter.id\n_fit_parameter.start_value\n'
        f'_fit_parameter.start_uncertainty\n{identity} 12.5 0.125\n'
    )
    path.write_text(path.read_text() + '\n' + added)
    project = engine.Project.load(source)
    destination = tmp_path / 'saved'
    project.save_as(destination)
    assert identity in (destination / 'analysis/analysis.edi').read_text().split(), (
        'Current public aliases and compact fit-state ids must retain their declared role'
    )
    engine.Project.load(destination)
