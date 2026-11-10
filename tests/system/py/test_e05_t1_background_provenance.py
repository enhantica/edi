""": producing declarations, never producer-generated labels, own provenance.

Native public API exercises the record producer, saved Analysis Text, both reloads,
historical settings changes and mixed-bank omission. Observations are closed form.
"""

from __future__ import annotations

import os
import runpy
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from conftest import crysta_reference_prefix

ROOT = Path(__file__).resolve().parents[3]
MODELS = ('line-segment', 'polynomial', 'chebyshev')
CASES = (
    tuple((m,) for m in MODELS)
    + tuple((m, m, m) for m in MODELS)
    + (
        ('line-segment', 'polynomial', 'line-segment'),
        ('polynomial', 'chebyshev', 'polynomial'),
        ('chebyshev', 'line-segment', 'chebyshev'),
    )
)
MATERIALIZE = runpy.run_path(str(ROOT / 'tests/fixtures/e05_t1/background_projects.py'))[
    'materialize'
]

SOURCE = r"""
#include "edi/io.hpp"
#include "edi/report.hpp"
#include <filesystem>
#include <fstream>
#include <iostream>
int main(int argc, char** argv) {
    if (argc != 5) return 2;
    try {
        auto project = edi::load_project(argv[1]);
        const bool cancelled = std::string(argv[4]) == "cancelled";
        auto callback = [cancelled]() { return cancelled; };
        auto result = project.fitting_mode == "joint" ? project.fit_joint({}, {}, callback)
                                                      : project.fit({}, {}, callback);
        const auto report = edi::machine_report(project, result, edi::VerbosityEnum::COMPACT);
        const auto pos = report.find("status=");
        std::cout << "report_status="
                  << report.substr(pos+7, report.find('\n', pos)-pos-7) << '\n';
        std::cout << "held=" << project.fit_result.background_function << '\n';
        edi::save_project_via_crysta(project, std::string(argv[3]) + "/first");
        auto first = edi::load_project(std::string(argv[3]) + "/first");
        project = first;
        std::cout << "reopened=" << project.fit_result.background_function << '\n';
        auto other = edi::load_project(argv[2]);
        project.experiments = other.experiments;
        edi::save_project_via_crysta(project, std::string(argv[3]) + "/changed");
        auto changed = edi::load_project(std::string(argv[3]) + "/changed");
        project = changed;
        std::cout << "changed=" << project.fit_result.background_function << '\n';
        edi::save_project_via_crysta(project, std::string(argv[3]) + "/again");
        return 0;
    } catch (const std::exception& error) { std::cerr << error.what(); return 1; }
}
"""


@pytest.fixture(scope='module')
def native_probe(tmp_path_factory):
    directory = tmp_path_factory.mktemp('background-native')
    source = directory / 'consumer.cpp'
    source.write_text(SOURCE)
    binary = directory / 'consumer'
    environment = Path(sys.executable).resolve().parent.parent
    compiler = shutil.which('clang++')
    assert compiler, ' the native provenance witness requires the pinned compiler'
    sdk = crysta_reference_prefix()
    build = Path(sys.modules['edi._edi'].__file__).resolve().parents[2]
    includes = [
        '-I' + str(ROOT / 'core/include'),
        '-I' + str(sdk / 'include'),
        '-I' + str(environment / 'include/eigen3'),
    ]
    libraries = [str(build / 'core/libedi_core.a'), str(sdk / 'lib/libcrysta_core.a')]
    command = [
        compiler,
        '-std=c++20',
        '-pthread',
        '-O0',
        *includes,
        str(source),
        *libraries,
        '-L' + str(environment / 'lib'),
        '-Wl,-rpath,' + str(environment / 'lib'),
        '-lsleef',
        '-lgomp' if sys.platform == 'linux' else '-lomp',
        '-o',
        str(binary),
    ]
    run = subprocess.run(command, capture_output=True, text=True, check=False, timeout=25)
    assert run.returncode == 0, (
        ' public API provenance witness must compile before its result counts: ' + run.stderr
    )
    return binary


def scalars(path):
    return dict(
        shlex.split(line)
        for line in path.read_text().splitlines()
        if line.startswith('_fit_result.') and len(shlex.split(line)) == 2
    )


@pytest.mark.parametrize('models', CASES, ids='+'.join)
@pytest.mark.parametrize('terminal', ['completed', 'cancelled'])
def test_producing_background_survives_fit_save_reopen_and_settings_change(
    native_probe, tmp_path, models, terminal
):
    source = MATERIALIZE(tmp_path / 'input', models)
    alternate = tuple(MODELS[(MODELS.index(model) + 1) % len(MODELS)] for model in models)
    other = MATERIALIZE(tmp_path / 'other', alternate)
    run = subprocess.run(
        [str(native_probe), str(source), str(other), str(tmp_path / 'saved'), terminal],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
        env={**os.environ, 'OMP_NUM_THREADS': '1'},
    )
    assert run.returncode == 0, (
        ' all declared-background fits and persistence routes must execute: ' + run.stderr
    )
    # These expectations come only from declarations passed to the visible generator.
    expected = models[0] if len(set(models)) == 1 else ''
    reported = dict(line.split('=', 1) for line in run.stdout.splitlines())
    assert reported['held'] == reported['reopened'] == reported['changed'] == expected, (
        ' the public held result and reloads retain the producing background; '
        'mixed banks omit an aggregate identity even when the first and last bank agree'
    )
    results = [
        scalars(tmp_path / 'saved' / step / 'analysis/analysis.edi')
        for step in ('first', 'changed', 'again')
    ]
    for result in results:
        assert result.get('_fit_result.background_function', '') == expected, (
            ' saved Analysis Text reports the background that produced the fit, '
            'never a hard-coded model or the current edited declaration'
        )
        assert ('_fit_result.background_function' in result) == bool(expected), (
            ' heterogeneous backgrounds omit the aggregate tag instead of writing '
            'a first-bank label or an empty placeholder'
        )
        assert result.get('_fit_result.result_kind') == 'deterministic', (
            ' provenance belongs to a retained real fit result'
        )
        if terminal == 'cancelled':
            assert result.get('_fit_result.exit_reason') == 'cancelled', (
                ' the cancellation control must reach a retained cancelled result'
            )
    assert results[0] == results[1] == results[2], (
        ' settings edits and repeated saves preserve the whole historical result'
    )
    assert reported['report_status'] == results[0]['_fit_result.exit_reason'], (
        ' the public report and saved historical result describe the same terminal state'
    )
