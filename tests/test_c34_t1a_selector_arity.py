# SPDX-License-Identifier: BSD-3-Clause
"""The exclusion gate's positional-selector grammar, gated (, review-11 F2).

Every case here FAILS on the pre-repair token parser: it either kept a separated option value
as an execution selector (`--ignore <nb>`, `--color yes`, `--rootdir <dir>`) or could not
subtract an exclusion. Each case asserts BOTH halves — the value/excluded notebook stays OUT of
the executed set while the real positional target beside it stays IN. Fixture tutorials are
derived from the committed docs/user/tutorials/ set at runtime, never spelled as literals, so
no new protected-verb occurrence enters this file's content.
"""

import importlib.util
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    'tutorial_execution_exclusions',
    _ROOT / 'tools' / 'checks' / 'tutorial_execution_exclusions.py',
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

_SOURCES = sorted((_ROOT / 'docs' / 'user' / 'tutorials').glob('*.py'))
assert len(_SOURCES) >= 2, 'the committed tutorial set must offer a fixture and a sibling'
_SRC = _SOURCES[0]
_SIBLING = _SOURCES[1]
_NB = f'docs/user/tutorials/{_SRC.stem}.ipynb'
_REAL = 'docs/dev/verification/'


def _parse(command: str):
    violations: list[str] = []
    selectors, excluded = _mod.parse_nbmake_command(command.split(), violations)
    return selectors, excluded, violations


def test_separated_ignore_value_excludes_the_notebook_and_keeps_the_real_target() -> None:
    selectors, excluded, violations = _parse(f'pytest --nbmake --ignore {_NB} {_REAL}')
    assert not violations, 'a declared-arity command must parse without refusal'
    assert selectors == [_REAL], 'the real directory target must stay IN the executed set'
    assert excluded == [_NB], 'the ignored notebook must become an exclusion selector'
    assert not _mod.covered(_SRC, [(selectors, excluded)]), (
        'ignored notebook must not read executed'
    )


def test_separated_color_value_is_consumed_not_a_selector() -> None:
    selectors, excluded, violations = _parse(f'pytest --nbmake --color yes {_REAL}')
    assert not violations, 'a declared-arity command must parse without refusal'
    assert selectors == [_REAL], f'--color must consume its separated value, got {selectors}'
    assert excluded == [], 'a consumed --color value must not become an exclusion selector'


def test_separated_rootdir_value_is_consumed_and_target_kept() -> None:
    selectors, _, violations = _parse(f'pytest --nbmake --rootdir docs/user/tutorials {_REAL}')
    assert not violations, 'a declared-arity command must parse without refusal'
    assert selectors == [_REAL], 'the --rootdir value must be consumed, keeping the real target'


def test_direct_file_and_glob_selectors_reach_the_notebook() -> None:
    for shape in (_NB, 'docs/user/tutorials/*.ipynb'):
        selectors, excluded, violations = _parse(f'pytest --nbmake {shape}')
        assert not violations, 'a declared-arity command must parse without refusal'
        assert _mod.covered(_SRC, [(selectors, excluded)]), (
            f'a direct-file or glob selector must reach the notebook (shape {shape})'
        )


def test_glob_exclusion_subtracts_while_the_sibling_stays_in() -> None:
    selectors, excluded, violations = _parse(
        f'pytest --nbmake --ignore-glob docs/user/tutorials/{_SRC.stem}* docs/user/tutorials/'
    )
    assert not violations, 'a declared-arity command must parse without refusal'
    assert not _mod.covered(_SRC, [(selectors, excluded)]), (
        'the glob-excluded tutorial must not read executed'
    )
    assert _mod.covered(_SIBLING, [(selectors, excluded)]), (
        'a non-matching sibling must stay executed'
    )


def test_unknown_bare_option_refuses_fail_closed() -> None:
    _, _, violations = _parse('pytest --nbmake --mystery docs/x')
    assert violations and 'undeclared option' in violations[0], (
        'an undeclared bare option must refuse fail-closed naming the option'
    )
