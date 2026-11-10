"""adapts : selector choices move from CLI options to project data.

Before: CLI --descent accepted registry ids and rejected unknown ids naming the set.
After: no minimization CLI option is accepted; project-loader registry validation is
covered in test_c34_t24_minimizer_declarations. The engine registry remains authoritative.
"""

from __future__ import annotations

import argparse

import edi.__main__ as cli
import pytest


def _fit_parser():
    parser = cli.build_parser()
    subcommands = next(
        action for action in parser._actions if isinstance(action, argparse._SubParsersAction)
    )
    return subcommands.choices['fit']


@pytest.mark.parametrize(
    'arguments',
    [
        ['--descent', 'ladder'],
        ['--descent', 'not_registered'],
        ['--list-descents'],
        ['--chi-square-tolerance', '1e-4'],
        ['--max-iter', '7'],
        ['--max-iterations', '7'],
    ],
)
def test_cli_refuses_every_minimization_option_as_unknown(arguments, capsys):
    with pytest.raises(SystemExit) as rejected:
        _fit_parser().parse_args(['project', *arguments])
    assert rejected.value.code != 0, ' minimization conditions belong in analysis.edi'
    error = capsys.readouterr().err
    assert 'unrecognized arguments' in error and arguments[0] in error, (
        ' removed options must be unknown, not accepted or interpreted as selectors'
    )


def test_fit_help_has_no_descent_listing_or_minimization_switch():
    help_text = _fit_parser().format_help()
    assert all(
        flag not in help_text
        for flag in ('--descent', '--list-descents', '--chi-square-tolerance', '--max-iter')
    ), ' CLI help must not advertise removed minimization conditions'
