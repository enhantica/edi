"""Owner ad40429ab: every notebook runs with only its built wheel and Jupyter closure."""

import copy
import json
import os
import shutil
from pathlib import Path

import nbformat
import pytest

from tests.fixtures.tutorial_cases.clean_wheel import assert_completed, run_one, wheel_contract
from tests.fixtures.tutorial_cases.contract import ROOT, cases_for
from tests.fixtures.tutorial_cases.install_cell import INSTALL_CELL
from tests.fixtures.tutorial_cases.notebook_fit import local_collection
from tests.fixtures.tutorial_cases.official_addresses import assert_public_addresses

CASES = sorted(
    set(cases_for('python'))
    | {path.stem for path in (ROOT / 'docs/user/tutorials').glob('*.ipynb')}
)


def built_wheel():
    given = os.environ.get('EDI_TUTORIAL_WHEEL')
    assert given, 'Gate 3/6: the wheel producer supplies EDI_TUTORIAL_WHEEL to the notebook gate'
    return Path(given).resolve()


def test_actual_wheel_metadata_carries_public_package_and_runtime_dependencies():
    wheel_contract(built_wheel())


@pytest.fixture(scope='module')
def clean_runs(tmp_path_factory, request):
    root = tmp_path_factory.mktemp('clean-wheel-notebooks')
    wheel = built_wheel()
    metadata = wheel_contract(wheel)
    given = os.environ.get('EDI_TUTORIAL_WHEELHOUSE')
    assert given and Path(given).is_dir(), (
        'Gate 3/6: pre-provision the Jupyter dependency wheel closure before the offline gate'
    )
    cache = Path(given)
    assert not list(cache.glob('easydiffraction-*.whl')), (
        'Gate 3/6: the offline dependency cache cannot replace the chosen built wheel'
    )
    wheels = root / 'wheels'
    wheels.mkdir()
    for source in [*cache.glob('*.whl'), wheel]:
        shutil.copy2(source, wheels / source.name)
    collection = (
        Path(os.environ['EDI_TUTORIAL_COLLECTION'])
        if os.environ.get('EDI_TUTORIAL_COLLECTION')
        else local_collection(root / 'collection')
    )
    assert (collection / 'index.json').is_file(), (
        'Gate 3/6: offline notebooks receive actual collection inputs, not mocked model answers'
    )
    inputs = root / 'inputs'
    inputs.mkdir()
    for case in CASES:
        source = ROOT / 'docs/user/tutorials' / (case + '.ipynb')
        if source.is_file():
            shutil.copy2(source, inputs / source.name)
    selected = {
        item.callspec.params['case']
        for item in request.session.items
        if item.module is request.module
        and hasattr(item, 'callspec')
        and 'case' in item.callspec.params
    }
    results = {}
    for case in sorted(selected):
        print('CLEAN_NOTEBOOK_BEGIN ' + case, flush=True)
        result = run_one(inputs / (case + '.ipynb'), root / case, wheels, collection)
        result['wheel_sha256'] = metadata['sha256']
        result['artifact_folder'] = str(root / case)
        results[case] = result
        (root / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
        print(
            'CLEAN_NOTEBOOK_END ' + case + ' ' + str(result['passed']) + ' ' + result['phase'],
            flush=True,
        )
    control = inputs / 'missing-runtime.ipynb'
    document = nbformat.v4.new_notebook(
        cells=[
            nbformat.v4.new_code_cell(INSTALL_CELL),
            nbformat.v4.new_code_cell('import visibly_missing_tutorial_runtime_dependency'),
            nbformat.v4.new_code_cell("print('UNREACHABLE_AFTER_MISSING_IMPORT')"),
        ]
    )
    document.cells[1].metadata['tags'] = ['raises-exception']
    nbformat.write(document, control)
    results['missing-runtime-control'] = run_one(
        control, root / 'missing-runtime-control', wheels, collection
    )
    (root / 'results.json').write_text(json.dumps(results, indent=2) + '\n')
    return results


@pytest.mark.parametrize('case', CASES)
def test_every_tutorial_executes_to_the_end_in_its_own_wheel_only_environment(case, clean_runs):
    assert_completed(clean_runs[case])


@pytest.mark.parametrize('case', CASES)
def test_executed_notebook_outputs_also_use_official_addresses(case, clean_runs):
    result = clean_runs[case]
    path = Path(result['artifact_folder']) / 'run-with-environment-witness.ipynb'
    assert path.is_file(), 'Gate 3/6: actual notebook execution produces inspectable output'
    document = json.loads(path.read_text())
    for cell in document['cells'][
        1:-1
    ]:  # The private environment witnesses are test instrumentation.
        assert_public_addresses(json.dumps(cell.get('outputs', []), ensure_ascii=False))


def test_clean_worker_reaches_and_propagates_an_actual_missing_runtime_import(clean_runs):
    result = clean_runs['missing-runtime-control']
    assert not result['passed'] and result.get('start'), (
        'Gate 3/6: the failing-import control reaches its clean kernel and actually fails'
    )
    assert 'ModuleNotFoundError' in result.get('error', '') and (
        'visibly_missing_tutorial_runtime_dependency' in result.get('error', '')
    ), 'Gate 3/6: a missing notebook dependency is exposed rather than patched or hidden'
    with pytest.raises(AssertionError, match='Gate 3/6:'):
        assert_completed(result)


@pytest.mark.parametrize(
    'damage',
    [
        'failed-cell',
        'no-finish',
        'changed-prefix',
        'extra-package',
        'source-import',
        'traversal',
        'preinstalled-wheel',
        'no-native',
    ],
)
def test_clean_environment_witness_refuses_each_leak_or_incomplete_execution(tmp_path, damage):
    prefix = tmp_path / 'env'
    before = {'prefix': str(prefix), 'installed': ['pip', 'ipykernel', 'nbclient']}
    after = {
        'prefix': str(prefix),
        'installed': ['pip', 'ipykernel', 'nbclient', 'easydiffraction'],
        'allowed': ['pip', 'ipykernel', 'nbclient', 'easydiffraction'],
        'origins': {
            'edi': str(prefix / 'edi/__init__.py'),
            'easydiffraction': str(prefix / 'easydiffraction/__init__.py'),
            'edi._edi': str(prefix / 'edi/_edi.abi3.so'),
        },
    }
    good = {'passed': True, 'start': before, 'finish': after}
    assert_completed(good)
    broken = copy.deepcopy(good)
    if damage == 'failed-cell':
        broken['passed'] = False
    elif damage == 'no-finish':
        broken['finish'] = None
    elif damage == 'changed-prefix':
        broken['finish']['prefix'] = str(tmp_path / 'other')
    elif damage == 'extra-package':
        broken['finish']['installed'].append('undeclared-notebook-helper')
    elif damage in {'source-import', 'traversal'}:
        broken['finish']['origins']['edi'] = str(
            tmp_path / 'checkout/edi.py' if damage == 'source-import' else prefix / '../edi.py'
        )
    elif damage == 'preinstalled-wheel':
        broken['start']['installed'].append('easydiffraction')
    else:
        del broken['finish']['origins']['edi._edi']
    with pytest.raises(AssertionError, match='Gate 3/6:'):
        assert_completed(broken)
