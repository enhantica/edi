"""gates for the crysta pin, truthful CW framing, and basin evidence."""

from __future__ import annotations

import ast
from pathlib import Path

from conftest import corpus_case_dir

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / 'examples/fit_lbco_hrpt.py'
ROOT_README = ROOT / 'README.md'


def _project() -> Path:
    return corpus_case_dir('lbco-hrpt-s2') / 'project'


def _project_readme() -> Path:
    # The CW template's claim README rides the promoted corpus case ( ruling 8d).
    return _project() / 'README.md'


BASELINE = ROOT / 'tests/fixtures/lbco_hrpt_baseline/baseline.json'
BASELINE_KEY = 'refine-lbco-hrpt-from-data'


def _module_docstring(path: Path) -> str:
    parsed = ast.parse(path.read_text(encoding='utf-8'))
    docstring = ast.get_docstring(parsed, clean=False)
    assert docstring is not None
    return docstring


def test_c11_t21_committed_surfaces_drop_retired_abort_and_cutoff_claims() -> None:
    surfaces = {
        SCRIPT.relative_to(ROOT): _module_docstring(SCRIPT),
        ROOT_README.relative_to(ROOT): ROOT_README.read_text(encoding='utf-8'),
        'corpus:lbco-hrpt-s2/project-README.md': _project_readme().read_text(encoding='utf-8'),
    }
    retired = (
        'raises mid-fit',
        'correctly refuses',
        'ValueError:',
        '0 paints nothing',
        'Until  closes',
        'issues/crysta/open/-',
        'issues/crysta/open/-',
    )
    stale = [
        f'{path}: {phrase}'
        for path, text in surfaces.items()
        for phrase in retired
        if phrase.casefold() in text.casefold()
    ]
    assert not stale, 'retired pin semantics remain on committed surfaces:\n' + '\n'.join(stale)
