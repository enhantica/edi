"""Review-10 F2: persisted companion priors obey the finite, classic numeric boundary."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import edi
import pytest

from tests.system.py.test_e09_t58_cli_persistence import (
    _stage_positional_project,  # noqa: PLC2701 - shared independent corpus staging
)

_LOCALE_CANDIDATES = ['de_DE.UTF-8', 'de_DE.utf8', 'German_Germany.1252']
_LOCALE_PROBE = """
import locale
import sys
for name in sys.argv[1:]:
    try:
        locale.setlocale(locale.LC_NUMERIC, name)
    except locale.Error:
        continue
    if locale.localeconv()['decimal_point'] == ',':
        print(name)
        raise SystemExit(0)
raise SystemExit(1)
"""
_LOAD_AND_UNDO = """
import json
import locale
import sys
import edi
locale.setlocale(locale.LC_NUMERIC, sys.argv[2])
if sys.argv[2] != 'C':
    assert locale.localeconv()['decimal_point'] == ','
    assert locale.atof('1,25') == 1.25
project = edi.Project.load(sys.argv[1])
site = next(site for site in project.structure.atom_sites if site.id == 'Al1')
prior = [site.fract_y.start_uncertainty, site.fract_z.start_uncertainty]
project._undo_fit()
restored = [site.fract_y.uncertainty, site.fract_z.uncertainty]
print(json.dumps({'prior': prior, 'restored': restored}, allow_nan=False))
"""


def _with_snapshot(destination: Path, payload: str) -> Path:
    project = _stage_positional_project(destination)
    analysis = project / 'analysis/analysis.edi'
    text = analysis.read_text(encoding='utf-8')
    assert '_fit_parameter.' not in text, 'the independent seed must have no prior snapshot'
    text = text.replace('_edi.schema_version 2', '_edi.schema_version 3')
    analysis.write_text(
        text
        + '\nloop_\n_fit_parameter.id\n_fit_parameter.start_value\n'
        + '_fit_parameter.start_uncertainty\n_fit_parameter.start_tied\n'
        + f'structure.Al1.fract_x 0.25193 0.00010 {payload}\n',
        encoding='utf-8',
    )
    return project


@pytest.mark.parametrize('payload', ['y=nan;z=.', 'y=inf;z=.', 'y=1.25e-3junk;z=.'])
def test_edi_start_tied_refuses_nonfinite_and_partial_numbers(
    tmp_path: Path, payload: str
) -> None:
    project = _with_snapshot(tmp_path / 'malformed', payload)
    with pytest.raises(edi.IoError, match=r'start_tied'):
        edi.Project.load(project)


@pytest.fixture(scope='module')
def comma_locale(tmp_path_factory: pytest.TempPathFactory) -> tuple[dict[str, str], str]:
    # Use a real C numeric locale: a C++ numpunct facet alone cannot challenge std::stod.
    # macOS provides named locales; minimal Linux images can compile one privately from
    # the system locale definitions. Nothing changes the runner's global locale or archive.
    env = os.environ.copy()
    probe = subprocess.run(
        [sys.executable, '-c', _LOCALE_PROBE, *_LOCALE_CANDIDATES],
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if probe.returncode != 0:
        localedef = shutil.which('localedef')
        assert localedef, 'the numeric boundary control requires a usable comma-decimal locale'
        locale_root = tmp_path_factory.mktemp('start-tied-locale')
        build = subprocess.run(
            [
                localedef,
                '--no-archive',
                '-i',
                'de_DE',
                '-f',
                'UTF-8',
                str(locale_root / 'de_DE.UTF-8'),
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        assert build.returncode == 0, (
            'the numeric boundary control must compile a private comma-decimal locale: '
            + build.stdout
            + build.stderr
        )
        env['LOCPATH'] = str(locale_root)
        probe = subprocess.run(
            [sys.executable, '-c', _LOCALE_PROBE, *_LOCALE_CANDIDATES],
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
    assert probe.returncode == 0, 'the alternate-locale control must actually select decimal comma'
    return env, probe.stdout.strip()


@pytest.mark.parametrize('numeric_locale', ['classic', 'comma'])
@pytest.mark.parametrize(
    ('payload', 'expected'),
    [('y=1.25e-3;z=0', [0.00125, 0.0]), ('y=.;z=0', [None, 0.0]), ('y=0;z=.', [0.0, None])],
    ids=['dotted-exponent', 'absent-zero', 'zero-absent'],
)
def test_edi_start_tied_is_locale_independent_and_preserves_optional_zero(
    tmp_path: Path,
    comma_locale: tuple[dict[str, str], str],
    numeric_locale: str,
    payload: str,
    expected: list[float | None],
) -> None:
    project = _with_snapshot(tmp_path / 'valid', payload)
    env, alternate = comma_locale
    selected = 'C' if numeric_locale == 'classic' else alternate
    result = subprocess.run(
        [sys.executable, '-c', _LOAD_AND_UNDO, str(project), selected],
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert result.returncode == 0, (
        'F2 valid start_tied numbers must load under the selected numeric locale: '
        + result.stdout
        + result.stderr
    )
    assert json.loads(result.stdout) == {'prior': expected, 'restored': expected}, (
        'F2 dotted/exponent values and absent-versus-zero state must survive loading and undo'
    )
