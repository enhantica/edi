"""Fresh wheel/Jupyter environments; no source overlays or extra runtime packages."""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import zipfile
from email.parser import BytesParser
from pathlib import Path

from packaging.requirements import Requirement


def wheel_contract(path):
    assert path.is_file() and path.suffix == '.whl', (
        'Gate 3/6: the notebook producer supplies the actual built wheel'
    )
    with zipfile.ZipFile(path) as archive:
        metadata = [name for name in archive.namelist() if name.endswith('.dist-info/METADATA')]
        assert len(metadata) == 1 and 'easydiffraction/__init__.py' in archive.namelist(), (
            'Gate 3/6: the built wheel contains one distribution and its public package'
        )
        document = BytesParser().parsebytes(archive.read(metadata[0]))
    assert document['Name'] == 'easydiffraction', (
        'Gate 3/6: the installed distribution is the public easydiffraction wheel'
    )
    dependencies = document.get_all('Requires-Dist', [])
    assert any(Requirement(raw).name.casefold() == 'numpy' for raw in dependencies), (
        'Gate 3/6: the actual shipped metadata declares its numerical dependency'
    )
    return {
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'name': document['Name'],
        'version': document['Version'],
        'requires': dependencies,
    }


def clean_environment(work, prefix, wheels, collection):
    env = {
        key: value
        for key, value in os.environ.items()
        if not key.startswith(('EDI_', 'CRYSTA_', 'PYTHON', 'JUPYTER', 'IPYTHON', 'PIP_', 'DYLD_'))
        and key not in {'LD_LIBRARY_PATH', 'LD_PRELOAD'}
    }
    env.update({
        'PATH': str(prefix / ('Scripts' if os.name == 'nt' else 'bin')) + os.pathsep + os.defpath,
        'PYTHONNOUSERSITE': '1',
        'PIP_CONFIG_FILE': os.devnull,
        'PIP_NO_INDEX': '1',
        'PIP_FIND_LINKS': str(wheels),
        'PIP_DISABLE_PIP_VERSION_CHECK': '1',
        'JUPYTER_PATH': str(work / 'jupyter/share'),
        'JUPYTER_CONFIG_DIR': str(work / 'jupyter/config'),
        'JUPYTER_DATA_DIR': str(work / 'jupyter/data'),
        'JUPYTER_RUNTIME_DIR': str(work / 'jupyter/runtime'),
        'IPYTHONDIR': str(work / 'ipython'),
        'EDI_COLLECTION': str(collection),
        'OMP_NUM_THREADS': '1',
        'OPENBLAS_NUM_THREADS': '1',
    })
    return env


def run_one(source, folder, wheels, collection, *, worker=None):
    folder.mkdir(parents=True)
    prefix = folder / 'env'
    python = prefix / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    env = clean_environment(folder, prefix, wheels, collection)
    result = {'passed': False, 'phase': 'input', 'source': str(source)}
    if not source.is_file():
        result['error'] = 'Gate 3/6: declared notebook is missing'
        return result
    staged = folder / source.name
    shutil.copy2(source, staged)
    result['source_sha256'] = hashlib.sha256(staged.read_bytes()).hexdigest()
    worker = worker or Path(__file__).with_name('wheel_worker.py')
    try:  # noqa: PLW0717 - all subprocess phases share one private environment cleanup
        with (folder / 'setup.log').open('w') as log:
            for phase, arguments in [
                ('venv', [sys.executable, '-m', 'venv', str(prefix)]),
                (
                    'jupyter',
                    [
                        str(python),
                        '-I',
                        '-m',
                        'pip',
                        'install',
                        '--no-index',
                        '--find-links',
                        str(wheels),
                        'ipykernel',
                        'nbclient',
                    ],
                ),
            ]:
                result['phase'] = phase
                completed = subprocess.run(
                    arguments,
                    cwd=folder,
                    env=env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    check=False,
                    timeout=180,
                )
                if completed.returncode:
                    result['error'] = 'Clean notebook setup failed; see setup.log'
                    return result
        assert 'include-system-site-packages = false' in (prefix / 'pyvenv.cfg').read_text(), (
            'Gate 3/6: a notebook environment never includes host site packages'
        )
        spec = folder / 'jupyter/share/kernels/edi-wheel-clean'
        spec.mkdir(parents=True)
        (spec / 'kernel.json').write_text(
            json.dumps({
                'argv': [str(python), '-I', '-m', 'ipykernel_launcher', '-f', '{connection_file}'],
                'display_name': 'Isolated built wheel',
                'language': 'python',
            })
        )
        result['phase'] = 'notebook'
        with (folder / 'notebook.log').open('w') as log:
            completed = subprocess.run(
                [str(python), '-I', str(worker), str(staged), str(folder)],
                cwd=folder,
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=False,
                timeout=3600,
            )
        if (folder / 'result.json').is_file():
            observed = json.loads((folder / 'result.json').read_text())
            result.update(observed)
            result['passed'] = completed.returncode == 0 and observed['passed']
        else:
            result.update(
                error='Clean notebook worker produced no execution witness',
                returncode=completed.returncode,
            )
    except subprocess.TimeoutExpired as error:
        result.update(phase='timeout', error=str(error))
    finally:
        # Keep source, outputs, logs and witnesses; only this case's private venv is disposable.
        shutil.rmtree(prefix, ignore_errors=True)
    return result


def assert_completed(result):
    assert result['passed'] and result.get('start') and result.get('finish'), (
        'Gate 3/6: every tutorial reaches its end using only the built wheel and Jupyter: '
        + result.get('phase', '')
        + ': '
        + result.get('error', '')
    )
    before, after = result['start'], result['finish']
    assert before['prefix'] == after['prefix'], (
        'Gate 3/6: notebook installation and its displays use the same fresh environment'
    )
    assert set(after['installed']) <= set(after['allowed']), (
        'Gate 3/6: installed notebook dependencies belong to the declared wheel/Jupyter closure'
    )
    assert 'easydiffraction' not in before['installed'], (
        'Gate 3/6: each notebook installs the wheel into an initially clean Jupyter environment'
    )
    assert {'edi', 'easydiffraction'} <= set(after.get('origins', {})), (
        'Gate 3/6: the final witness includes the public facade and implementation origins'
    )
    assert any(path.endswith(('.so', '.pyd')) for path in after['origins'].values()), (
        'Gate 3/6: the final environment witness includes the compiled wheel extension'
    )
    prefix = Path(after['prefix']).resolve()
    assert after.get('origins') and all(
        Path(path).resolve().is_relative_to(prefix) for path in after['origins'].values()
    ), 'Gate 3/6: public Python and native imports resolve only to the installed built wheel'
