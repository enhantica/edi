"""Capture original Windows calculation bytes, refusing every later product or engine."""

import argparse
import base64
import hashlib
import importlib
import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

PRODUCT = '7a8eabf53084332a10b90991907d2040e5365b6a'
ENGINE = 'b9f2267451adf1896463c706a87fea20790d28ac'
HOME = Path(__file__).resolve().parent


def require(condition, message):
    if not condition:
        raise ValueError(message)


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def capture(args):  # noqa: PLR0914, PLR0915 - one complete source/artifact custody record
    require(
        platform.system() == 'Windows'
        and platform.machine().lower() in {'amd64', 'x86_64'}
        and sys.maxsize > 2**32,
        'Capture requires a native Windows x64 process',
    )
    require(
        'CRYSTA_SIMD_LANES' not in os.environ, 'Capture retains original default native dispatch'
    )
    for source, wanted in [(args.product, PRODUCT), (args.engine, ENGINE)]:
        require(
            git(source, 'rev-parse', 'HEAD') == wanted,
            'Capture requires each exact original source commit',
        )
        subprocess.run(['git', '-C', str(source), 'diff', '--exit-code', 'HEAD'], check=True)
        require(
            not git(source, 'ls-files', '--others', '--exclude-standard'),
            'Capture requires pristine historical source checkouts',
        )
    hashes = json.loads((HOME / 'rename-input-sha256.json').read_text())
    inputs = HOME / 'rename_inputs'
    require(
        {p.relative_to(inputs).as_posix(): digest(p) for p in inputs.rglob('*.edi')} == hashes,
        'Capture requires every original LF serialized input byte',
    )
    original = json.loads((HOME / 'tch-regression-Linux.json').read_text())
    require(
        original['source'] == PRODUCT and original['engine_source'] == ENGINE,
        'The retained sample population comes from the original capture',
    )
    library, executable = args.prefix / 'lib/crysta_core.lib', args.prefix / 'bin/crysta.exe'
    require(
        library.is_file() and executable.is_file(),
        'Capture requires the freshly installed original native archive and CLI',
    )
    compiled = subprocess.check_output([str(executable), '--build-commit'], text=True).strip()
    require(compiled == ENGINE, 'The original compiled engine must attest its own source')
    archives = [
        p for p in args.engine_build.rglob('crysta_core.lib') if digest(p) == digest(library)
    ]
    require(len(archives) == 1, 'The installed archive equals the original build artifact')
    cache = (args.build / 'CMakeCache.txt').read_text()
    package = next(
        (line.split('=', 1)[1] for line in cache.splitlines() if line.startswith('crysta_DIR:')),
        '',
    )
    require(
        Path(package).resolve() == (args.prefix / 'lib/cmake/crysta').resolve(),
        'Edi links the exact freshly built historical package',
    )
    handles = []
    for folder in [args.prefix / 'bin', Path(sys.prefix) / 'Library/bin']:
        if folder.is_dir():
            handles.append(os.add_dll_directory(str(folder)))  # noqa: PERF401 - retain DLL registrations for the complete native run
    sys.path.insert(0, str(args.product / 'lib'))
    os.environ['EDI_EXTENSION_DIR'] = str(args.build / 'python/edi')
    for key in ['EDI_USE_CONSUMER_BUILD', 'CRYSTA_CONSUMER_SRC', 'CRYSTA_SDK_DIR']:
        os.environ.pop(key, None)
    require('edi' not in sys.modules, 'Capture refuses a previously imported product module')
    spec = importlib.util.spec_from_file_location(
        'edi',
        args.product / 'lib/edi/__init__.py',
        submodule_search_locations=[str(args.product / 'lib/edi')],
    )
    edi = importlib.util.module_from_spec(spec)
    sys.modules['edi'] = edi
    spec.loader.exec_module(edi)
    require(
        edi.__build_commit__ == PRODUCT,
        'The actual imported historical module attests its original source',
    )
    module = Path(sys.modules['edi._edi'].__file__).resolve()
    require(
        module.parent == (args.build / 'python/edi').resolve(),
        'Capture imports the explicit physical native module',
    )
    spec = importlib.util.spec_from_file_location(
        'edi.verification', args.product / 'lib/edi/verification.py'
    )
    verification = importlib.util.module_from_spec(spec)
    sys.modules['edi.verification'] = verification
    spec.loader.exec_module(verification)
    require(
        verification._crysta_provenance_path().read_text().strip() == ENGINE,
        'Linked provenance agrees with the actual original CLI and package',
    )
    np = importlib.import_module('numpy')
    pins = {}
    for name in ['tch', 'fcj']:
        project_path = args.work / name
        shutil.copytree(inputs / name, project_path)
        project = edi.Project.load(project_path)
        project.analysis.calculate()
        values = np.asarray(project.experiments[0].data.intensity_calc, dtype='<f8')
        require(
            values.nbytes == len(base64.b64decode(original['pins'][name], validate=True))
            and np.isfinite(values).all(),
            'The native capture retains every finite original sample',
        )
        pins[name] = base64.b64encode(values.tobytes()).decode('ascii')
    manifest = {
        'platform': 'win-64',
        'source_sha': ENGINE,
        'tested': {
            'sha256': {
                'lib/crysta_core.lib': digest(library),
                'bin/crysta.exe': digest(executable),
            }
        },
    }
    record = {
        'source': PRODUCT,
        'engine_source': ENGINE,
        'kind': 'regression-pin',
        'platform': 'Windows',
        'architecture': platform.machine(),
        'input_sha256': hashes,
        'sdk_manifest': manifest,
        'pins': pins,
        'module_sha256': digest(module),
        'capture_sha256': digest(Path(__file__)),
        'linux_capture_sha256': digest(HOME / 'tch-regression-Linux.json'),
        'run_id': os.environ.get('GITHUB_RUN_ID'),
        'run_attempt': os.environ.get('GITHUB_RUN_ATTEMPT'),
    }
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'tch-regression-Windows.json').write_text(
        json.dumps(record, indent=2) + '\n', encoding='utf-8', newline='\n'
    )
    for name, root in [('product', args.product), ('engine', args.engine)]:
        (args.output / (name + '-tree.txt')).write_text(
            git(root, 'rev-parse', 'HEAD^{tree}') + '\n', encoding='utf-8', newline='\n'
        )
    for name, path in [
        ('product-CMakeCache.txt', args.build / 'CMakeCache.txt'),
        ('engine-CMakeCache.txt', args.engine_build / 'CMakeCache.txt'),
    ]:
        shutil.copyfile(path, args.output / name)
    proof = {
        **{key: value for key, value in record.items() if key != 'pins'},
        'python': sys.version,
        'module': str(module),
        'compiled_engine': compiled,
    }
    (args.output / 'capture-provenance.json').write_text(
        json.dumps(proof, indent=2) + '\n', encoding='utf-8', newline='\n'
    )
    print(
        json.dumps({
            'output': str(args.output),
            'source': PRODUCT,
            'engine': ENGINE,
            'pin_sha256': digest(args.output / 'tch-regression-Windows.json'),
        })
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for argument in ['product', 'engine', 'build', 'engine-build', 'prefix', 'work', 'output']:
        parser.add_argument('--' + argument, type=Path, required=True)
    capture(parser.parse_args())
