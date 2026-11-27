"""Check the documentation runner's two measured-data entry points."""

import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
EXAMPLE = 'pd-neut-cwl_y2o3-spodi'
ROWS = '21.5 17.25 0.75\n22.75 31.75 1.25\n25.125 23.5 1.5\n'


@pytest.fixture(scope='module')
def capture_results(tmp_path_factory):
    binary = Path(os.environ.get('EDI_DOCS_APP', ROOT / 'build/app/app/edi_app'))
    assert binary.is_file(), 'Documentation import needs the current native capture executable'
    root = tmp_path_factory.mktemp('capture-data')
    results = {}
    for operation in ('import-data', 'import-scan'):
        for valid in (True, False):
            case = root / f'{operation}-{valid}'
            case.mkdir()
            first = case / 'capture-01.xye'
            first.write_text(ROWS if valid else 'not measured data\n', encoding='utf-8')
            names = [first.name]
            source = first
            if operation == 'import-scan':
                second = case / 'capture-02.xye'
                second.write_text(ROWS, encoding='utf-8')
                names.append(second.name)
                source = case
            # Keep the script and output outside the folder passed to the scan picker.
            script = root / f'{case.name}.js'
            actions = [
                f'open-cli-project:{EXAMPLE}',
                'appBar.tab.experiment',
                'sideBar.tab.basic',
                'expand:group.experiments',
                f'{operation}:{source}',
            ]
            step = {
                'id': 'loaded-data',
                'page': 'experiment',
                'description': 'Publish the measured-data input',
                'actions': actions,
                'highlights': [
                    f'experiments.file.{i}' for i in range(len(names))
                ] if valid else [],
            }
            script.write_text(
                f'({{schema: 2, workflow: "reference", example: "{EXAMPLE}", '
                f'build: function() {{ return {json.dumps([step])}; }}}})\n',
                encoding='utf-8',
            )
            output = root / f'{case.name}-output'
            run = subprocess.run(
                ['bash', 'tools/docs/capture-gui.sh', output, '--docs-script', script],
                cwd=ROOT,
                env={**os.environ, 'EDI_DOCS_APP': str(binary)},
                capture_output=True,
                text=True,
                check=False,
                timeout=90,
            )
            manifest_path = output / 'manifest.json'
            assert manifest_path.is_file(), (
                f'The native runner must report the {operation} outcome: {run.stderr}'
            )
            manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
            results[operation, valid] = (run.returncode, manifest, output, names)
    return results


@pytest.mark.parametrize('operation', ['import-data', 'import-scan'])
def test_capture_import_outcome_follows_its_own_read(capture_results, operation):
    code, manifest, output, names = capture_results[operation, True]
    assert code == 0 and manifest['status'] == 'complete', (
        f'The capture must finish after a successful {operation}: {manifest.get("error")}'
    )
    scene = next(scene for scene in manifest['scenes'] if scene['id'] == 'loaded-data')
    layout = json.loads((output / scene['metadata']).read_text(encoding='utf-8'))
    actual = [layout['items'][f'experiments.file.{i}']['label'] for i in range(len(names))]
    assert actual == names, (
        'The next captured frame must show the fixture files admitted by this read'
    )

    bad_code, refused, _, _ = capture_results[operation, False]
    assert bad_code != 0 and refused['status'] == 'failed' and operation in {
        action['action'].split(':', 1)[0] for action in refused['actions']
    }, f'The capture must reach {operation} and report the read refusal as a failure'
    assert not refused['scenes'] and 'cannot load' in refused['error'], (
        'A refused read cannot publish a successful capture scene'
    )
