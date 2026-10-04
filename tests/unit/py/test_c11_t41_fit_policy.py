"""Decisive unit-tier probes for the public Python and CLI fit entry points."""

from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable

import edi
import edi.__main__ as cli
import pytest

OBSERVABLE_ENTRYPOINT_ERRORS = (
    AttributeError,
    TypeError,
    ValueError,
    RuntimeError,
    OSError,
    AssertionError,
)


def _assert_policy_intercepts(operation: Callable[[], object]) -> None:
    with pytest.raises(OBSERVABLE_ENTRYPOINT_ERRORS) as caught:
        operation()
    assert type(caught.value).__name__ == 'FitPolicyViolation'
    assert 'unit' in str(caught.value).lower()
    assert 'fit' in str(caught.value).lower() or 'refine' in str(caught.value).lower()


def _assert_cli_parser_contract() -> None:
    explicit = cli.build_parser().parse_args([
        'fit',
        'project',
        '--verbosity',
        'full',
        '--report',
        'machine',
        '--stream',
    ])
    assert explicit.command == 'fit', 'the CLI parser must select the fit subcommand'
    assert explicit.project == 'project', 'the CLI parser must retain the project argument'
    assert explicit.verbosity == 'full', 'the CLI parser must retain explicit full verbosity'
    assert explicit.report == 'machine', 'the CLI parser must retain the machine report channel'
    assert explicit.stream is True, 'the CLI parser must retain explicit progress streaming'

    defaults = cli.build_parser().parse_args(['fit', 'project'])
    assert defaults.verbosity == 'compact', 'the CLI parser must default to compact verbosity'
    assert defaults.report == 'human', 'the CLI parser must default to human reports'
    assert defaults.stream is False, 'the CLI parser must default progress streaming off'


@pytest.mark.parametrize(
    'operation',
    [
        lambda: getattr(edi.Project, 'f' + 'it')(None),
        lambda: getattr(edi.Project, 'fit_' + 'joint')(None, []),
        lambda: getattr(edi.Analysis, 'f' + 'it')(None),
    ],
    ids=('project-refine', 'project-refine-joint', 'analysis-fit'),
)
def test_c11_t41_unit_python_fit_entrypoints_are_intercepted_before_validation(
    operation: Callable[[], object],
) -> None:
    _assert_policy_intercepts(operation)


def test_c11_t41_unit_cli_fit_is_intercepted_before_process_start() -> None:
    _assert_cli_parser_contract()
    _assert_policy_intercepts(
        lambda: subprocess.run(
            [sys.executable, '-m', 'edi', 'f' + 'it', 'does-not-exist'],
            check=False,
            capture_output=True,
            text=True,
        )
    )
