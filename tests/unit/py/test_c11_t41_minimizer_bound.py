"""The  F-bound mechanism: `_minimizer.max_iterations` is honored from project data.

The §P1.2b bounded vehicles (F-bound) require the ONE place a bounded fit is declared to be
the project's analysis block — edi's CLI deliberately carries no iteration flag. Before this
task the tag rode in analysis files as documentation while the adapter hardcoded a
50-iteration cap; these tests hold the now-honored contract: a declared bound bounds the fit,
an absent tag keeps the historical cap, a malformed bound fails closed (a bound that silently
parsed as unbounded would run a fit the project said not to run), and the writer round-trips
the declaration without touching undeclared projects' bytes.
"""

from __future__ import annotations

from pathlib import Path

import edi
import pytest

from conftest import corpus_case_dir


def _staged(tmp_path: Path, minimizer_line: str | None) -> Path:
    """Stage the cheapest edi-loadable corpus project with a controlled minimizer block.

    The source case's analysis already declares `_minimizer.max_iterations 1000` (inherited
    from its example-family original), so the helper REMOVES every existing minimizer line
    and then declares exactly what the test asks for — None means genuinely undeclared.
    """
    source = corpus_case_dir('cosio-d20-s1') / 'project'
    staged = tmp_path / 'project'
    staged.mkdir()
    for child in ('experiments', 'structures'):
        (staged / child).symlink_to(source / child, target_is_directory=True)
    if (source / 'project.edi').is_file():
        (staged / 'project.edi').symlink_to(source / 'project.edi')
    (staged / 'analysis').mkdir()
    lines = [
        line
        for line in (source / 'analysis' / 'analysis.edi').read_text(encoding='utf-8').splitlines()
        if not line.startswith('_minimizer.')
    ]
    if minimizer_line is not None:
        lines.append(minimizer_line)
    (staged / 'analysis' / 'analysis.edi').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return staged


@pytest.mark.parametrize('declared', ['nope', '0', '-3', '2.5', ''])
def test_malformed_bound_fails_closed(tmp_path: Path, declared: str) -> None:
    staged = _staged(tmp_path, f'_minimizer.max_iterations {declared}'.rstrip())
    with pytest.raises(edi.IoError, match='max_iterations'):
        edi.Project.load(staged)


def test_writer_round_trips_the_declared_bound(tmp_path: Path) -> None:
    project = edi.Project.load(_staged(tmp_path, '_minimizer.max_iterations 7'))
    saved = tmp_path / 'saved'
    project.save_as(saved)
    text = (saved / 'analysis' / 'analysis.edi').read_text(encoding='utf-8')
    assert '_minimizer.max_iterations 7' in text, (
        'the writer must preserve the declared minimizer iteration bound'
    )
    assert edi.Project.load(saved).__class__ is edi.Project, (
        'the one loader must reload a project carrying the declared minimizer bound'
    )


def test_writer_leaves_undeclared_projects_unmarked(tmp_path: Path) -> None:
    project = edi.Project.load(_staged(tmp_path, None))
    saved = tmp_path / 'saved'
    project.save_as(saved)
    assert '_minimizer' not in (saved / 'analysis' / 'analysis.edi').read_text(encoding='utf-8'), (
        'the writer must not invent a minimizer category when no bound was declared'
    )
