"""Execute the production publication metadata seam without Qt or app CI.

Value-only publication must preserve the selected parameter population. The
vehicle holds independent category metadata for two structures and an experiment;
real coefficient and cell selections are positive controls. No pattern-change
claim is made for the minor phase.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


def _function(path, signature):
    text = path.read_text()
    start = text.index(signature)
    opening = text.index('{', start)
    depth = 1
    closing = opening + 1
    while depth:
        depth += (text[closing] == '{') - (text[closing] == '}')
        closing += 1
    return text[start:closing]


@pytest.fixture(scope='module')
def count_probe(tmp_path_factory):
    directory = tmp_path_factory.mktemp('live-count')
    registry = ROOT / 'app/src/parameter_registry.cpp'
    bodies = [
        _function(registry, 'void ParameterRegistry::refreshRefinable('),
        _function(registry, 'void ParameterRegistry::publish('),
        _function(ROOT / 'app/src/parameter_item.cpp', 'void ParameterItem::setRefinable('),
    ]
    template = ROOT / 'tests/fixtures/cwl_family/parameter_count_probe.cpp'
    source = directory / 'probe.cpp'
    source.write_text(
        template.read_text().replace('// INSERT_PRODUCTION_BODIES', '\n'.join(bodies))
    )
    compiler = shutil.which(os.environ.get('CXX', 'c++'))
    assert compiler, 'The metadata publication gate requires the runner C++ compiler'
    executable = directory / 'probe'
    result = subprocess.run(
        [compiler, '-std=c++20', str(source), '-o', str(executable)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        'The unchanged production metadata publication bodies must compile in the '
        'Qt-free boundary vehicle: ' + result.stderr
    )
    yield executable
    shutil.rmtree(directory)


@pytest.mark.parametrize(
    'vehicle', ['second-structure', 'experiment-fields', 'experiment-asymmetry']
)
def test_live_value_publication_preserves_parameter_population(count_probe, vehicle):
    result = subprocess.run([str(count_probe), vehicle], capture_output=True, text=True, timeout=5)
    assert result.returncode == 0, (
        'A second-structure value edit must preserve parameter membership and '
        'free/fixed counts through production publication for every category field: '
        + result.stderr
    )
