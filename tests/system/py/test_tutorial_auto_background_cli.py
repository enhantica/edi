"""Owner fd75d9139: both real CLI entries settle saved Auto settings before fitting."""

import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.fixtures.background_estimate.fitted_baseline import HERE, stored_pattern
from tests.fixtures.tutorial_cases.contract import ROOT


def points(path):
    tags, rows = [], []
    for line in path.read_text().splitlines():
        words = shlex.split(line, comments=True)
        if words == ['loop_']:
            tags = []
        elif len(words) == 1 and words[0].startswith('_'):
            tags.append(words[0])
        elif words and len(words) == len(tags) and '_background.intensity' in tags:
            rows.append(dict(zip(tags, words, strict=True)))
    return rows


@pytest.mark.parametrize('entry', ['python', 'standalone'])
def test_saved_auto_file_settles_its_requested_background_point_count_and_really_fits(
    entry, tmp_path
):
    destination = tmp_path / 'project'
    shutil.copytree(HERE / 'projects/fitted-auto-line-segment', destination)
    experiment = destination / 'experiments/d20.edi'
    original = experiment.read_text()
    assert '_background_estimate.mode auto' in original and len(points(experiment)) != 17, (
        'Gate 7: the declared corpus variant starts in Auto with a different saved point count'
    )
    changed, replacements = re.subn(
        r'(?m)^_background_estimate.n_points\s+\d+', '_background_estimate.n_points 17', original
    )
    assert replacements == 1, (
        'Gate 7: the Auto input explicitly requests seventeen estimate points'
    )
    experiment.write_text(changed)
    analysis = next((destination / 'analysis').glob('*.edi'))
    analysis.write_text(
        re.sub(
            r'(?m)^_minimizer.max_iterations\s+\d+',
            '_minimizer.max_iterations 3',
            analysis.read_text(),
        )
    )
    structure = next((destination / 'structures').glob('*.edi'))
    structure.write_text(
        re.sub(
            r'(?m)^(_cell.length_a\s+)([^\s()]+)(?:\([^)]*\))?',
            r'\g<1>\g<2>()',
            structure.read_text(),
        )
    )
    if entry == 'python':
        prefix = [sys.executable, '-m', 'edi']
    else:
        candidates = [
            os.environ.get('EDI_CLI_EXECUTABLE'),
            ROOT / 'build/ci-consumer/cli/easydiffraction',
            ROOT / 'build/ci/cli/easydiffraction',
        ]
        binary = next((str(path) for path in candidates if path and Path(path).is_file()), None)
        assert binary is not None, 'Gate 7 prerequisite: build the real standalone executable'
        prefix = [binary]
    result = subprocess.run(
        prefix + ['fit', str(destination)],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
        env={**os.environ, 'OMP_NUM_THREADS': '1', 'OPENBLAS_NUM_THREADS': '1'},
    )
    assert result.returncode == 0, (
        'Gate 7: the Auto project actually fits through each CLI entry: ' + result.stderr
    )
    assert len(points(experiment)) == 17, (
        'Gate 7: inspect saved bytes before any Python reload can mask a missing CLI estimate'
    )
    assert '_background_estimate.mode auto' in experiment.read_text(), (
        'Gate 7: CLI fitting preserves Auto mode'
    )
    saved = analysis.read_text()
    iterations = re.findall(r'(?m)^_fit_result.iterations\s+(\d+)', saved)
    assert iterations and int(iterations[-1]) > 0, (
        'Gate 7: this workflow reaches an actual nonempty fit'
    )
    pattern = stored_pattern(destination)
    assert len(pattern) > 0 and any(row[1] != 0 for row in pattern), (
        'Gate 7: the actual CLI fit publishes a calculated, estimated-background pattern'
    )
