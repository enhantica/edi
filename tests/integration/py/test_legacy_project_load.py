"""Older saved start-state names must be refused, without touching their input."""

import shutil
from pathlib import Path

import edi as engine
import pytest

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / 'tests/fixtures/legacy_project_load'


@pytest.mark.parametrize('kind', ['line-segment', 'polynomial', 'chebyshev'])
def test_old_engine_start_state_is_refused_with_its_name(kind, tmp_path):
    source = tmp_path / 'input'
    shutil.copytree(FIXTURE / kind, source)
    path = source / 'analysis/analysis.edi'
    text = path.read_text()
    # Manufacture the old writer's position name at the boundary, so no committed
    # project fixture itself depends on the retired format.
    start = text.index('_fit_parameter.start_tied')
    prefix, rows = text[:start], text[start:]
    lines = rows.splitlines()
    fields = lines[1].split()
    fields[0] = 'bank.background[0]'
    lines[1] = ' '.join(fields)
    path.write_text(prefix + '\n'.join(lines) + '\n')
    before = {p.relative_to(source): p.read_bytes() for p in source.rglob('*') if p.is_file()}
    with pytest.raises((ValueError, RuntimeError)) as caught:
        engine.Project.load(source)
    message = str(caught.value)
    assert 'bank.background[0]' in message, (
        'A saved positional start-state slot must be refused with the name that was found'
    )
    assert 'older version' in message.lower(), (
        'Older saved slots must request a current-format project rather than guessing ids'
    )
    assert len(message) <= 240, 'An older saved-slot refusal must remain a short load message'
    assert {
        p.relative_to(source): p.read_bytes() for p in source.rglob('*') if p.is_file()
    } == before, (
        'An older project refusal must preserve its scientific input and assigned start states'
    )
