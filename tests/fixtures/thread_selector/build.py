"""Observe real fills and preferences in private app and qualified SDK source copies."""

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tarfile
from pathlib import Path

from tests.fixtures.app_environment.closure import (
    dependencies,
    seal_bundle,
    validate_bundle,
    validate_dependencies,
)
from tests.fixtures.scan_app.build_probe import fingerprint, sdk_inputs, validate_current_inputs
from tests.fixtures.scan_screen.build import browser_configuration, run

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
ESCAPES = ('ignored-setter', 'thread-local', 'ignored-persistence', 'serial-fill')


def archive(root, revision, destination):
    destination.mkdir(parents=True, exist_ok=True)
    archive_path = destination.parent / (destination.name + '.tar')
    with archive_path.open('wb') as stream:
        run(['git', '-C', root, 'archive', revision], stdout=stream)
    with tarfile.open(archive_path) as stream:
        for member in stream.getmembers():
            if member.issym():
                target = root / member.name
                if target.is_file():
                    (destination / member.name).write_bytes(target.read_bytes())
            else:
                target = destination / member.name
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                elif member.isfile():
                    data = stream.extractfile(member).read()
                    target.parent.mkdir(parents=True, exist_ok=True)
                    if not target.exists() or target.read_bytes() != data:
                        target.write_bytes(data)
                        target.chmod(member.mode)
                else:
                    raise RuntimeError('Qualified app snapshots permit only files and directories')


def instrument_engine(source, escape):  # noqa: ARG001 - runtime controls share one real binary
    fixture = source / 'tests/fixtures/thread_selector'
    shutil.copytree(
        HERE, fixture, dirs_exist_ok=True, ignore=shutil.ignore_patterns('__pycache__')
    )
    path = source / 'src/core/parallel.hpp'
    text = path.read_text()
    marker = 'const std::size_t chunks = parallel_chunk_count(n_items, chunks_per_thread);'
    if text.count(marker) != 1 or text.count('body(std::size_t{0}, n_items);') != 1:
        raise RuntimeError('Worker observers must bind the real fill and its serial arm')
    text = text.replace(
        marker, marker + '\n    const auto observed_fill = thread_selector_fill(n_items, chunks);'
    )
    text = text.replace(
        'body(std::size_t{0}, n_items);',
        'thread_selector_worker(observed_fill);\n            body(std::size_t{0}, n_items);',
    )
    marker = 'const auto run_chunk = [&](std::ptrdiff_t index) {'
    if text.count(marker) != 1:
        raise RuntimeError('Worker observers must record identities inside the actual chunk body')
    text = text.replace(marker, marker + '\n        thread_selector_worker(observed_fill);')
    text = text.replace(
        '    const std::size_t base = n_items / chunks;',
        '    if (thread_selector_escape("serial-fill")) { '
        'thread_selector_worker(observed_fill); body(0, n_items); return; }\n'
        '    const std::size_t base = n_items / chunks;',
    )
    path.write_text('#include "../../tests/fixtures/thread_selector/engine_observer.hpp"\n' + text)
    cmake = source / 'CMakeLists.txt'
    cmake.write_text(
        cmake.read_text() + '\ntarget_sources(crysta_core PRIVATE '
        'tests/fixtures/thread_selector/engine_observer.cpp)\n'
    )
    path = source / 'src/core/threading.cpp'
    text = path.read_text()
    setter = 'void set_thread_count(int count) noexcept {'
    getter = 'int thread_count_setting() noexcept {'
    if text.count(setter) != 1 or text.count(getter) != 1:
        raise RuntimeError('Thread-local escape must reach the actual process-wide API')
    text = text.replace(
        setter,
        setter + '\n if(thread_selector_escape("thread-local")) {'
        ' thread_selector_local_count=count; return; }',
    )
    text = text.replace(
        getter,
        getter + '\n if(thread_selector_escape("thread-local"))'
        ' return thread_selector_local_count;',
    )
    path.write_text(
        '#include "../../tests/fixtures/thread_selector/engine_observer.hpp"\n'
        'static thread_local int thread_selector_local_count=0;\n' + text
    )


def instrument_app(source, escape):  # noqa: ARG001 - controls are selected at execution
    shutil.copytree(
        HERE,
        source / 'tests/fixtures/thread_selector',
        dirs_exist_ok=True,
        ignore=shutil.ignore_patterns('__pycache__'),
    )
    main = source / 'app/main.cpp'
    text = main.read_text()
    marker = '    edi_app::install_web_page_hooks(engine);'
    if text.count(marker) != 1:
        raise RuntimeError('Selector observation must bind the real QML host after load')
    text = text.replace(marker, '    thread_selector_install(engine);\n' + marker)
    text = text.replace(
        '    edi_app::configure_engine(engine);',
        '    edi_app::configure_engine(engine);\n    thread_selector_settings(engine);',
    )
    text, count = re.subn(
        r'(int main\([^)]*\)\s*\{)', r'\1\n thread_selector_environment();', text
    )
    if count != 1:
        raise RuntimeError('The browser caller environment must precede the actual first fill')
    main.write_text(
        'void thread_selector_environment();\n'
        'void thread_selector_install(class QQmlApplicationEngine&);\n'
        'void thread_selector_settings(class QQmlApplicationEngine&);\n' + text
    )
    path = source / 'app/CMakeLists.txt'
    path.write_text(
        path.read_text() + '\ntarget_sources(edi_app PRIVATE '
        '${PROJECT_SOURCE_DIR}/tests/fixtures/thread_selector/observe.cpp)\n'
    )
    path = source / 'app/qml/Globals/Preferences.qml'
    text = path.read_text()
    marker = 'category: "develop"'
    if text.count(marker) != 1:
        raise RuntimeError('Persistence escape must reach the actual machine category')
    path.write_text(
        text.replace(
            marker,
            'category: threadSelectorEscape === "ignored-persistence" '
            '? "discarded develop" : "develop"',
        )
    )
    path = source / 'core/src/adapter.cpp'
    text = path.read_text()
    marker = 'crysta::threading::set_thread_count(count);'
    if text.count(marker) != 1:
        raise RuntimeError('Ignored setter escape must reach the actual edi wrapper')
    path.write_text(
        'extern "C" bool thread_selector_escape(const char*);\n'
        + text.replace(marker, 'if (!thread_selector_escape("ignored-setter")) ' + marker)
    )


def build(root, output, sdk, engine_source, backend, escape=None):  # noqa: PLR0914, PLR0915 - qualified build and capture checks
    shared_inputs = dependencies('selector', root)
    compiled_sdk = sdk_inputs(sdk, engine_source)
    output.mkdir(parents=True, exist_ok=True)
    fixture_hashes = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in HERE.iterdir() if p.is_file()
    }
    manifest = json.loads((sdk / 'share/crysta-sdk/manifest.json').read_text())
    engine_sha = manifest['source_sha']
    app_sha = subprocess.check_output(['git', '-C', root, 'rev-parse', 'HEAD'], text=True).strip()
    app_source = output / 'source'
    archive(root, app_sha, app_source)
    production = fingerprint(app_source)
    engine = output / 'engine-source'
    if (engine_source / '.git').exists():
        archive(engine_source, engine_sha, engine)
    else:
        shutil.copytree(
            engine_source,
            engine,
            dirs_exist_ok=True,
            ignore=shutil.ignore_patterns('.pixi', 'build', '__pycache__'),
        )
    before_engine = {
        str(p.relative_to(engine)): hashlib.sha256(p.read_bytes()).hexdigest()
        for part in ('src', 'include')
        for p in sorted((engine / part).rglob('*'))
        if p.is_file()
    }
    selected_sources = {
        name: digest
        for name, digest in compiled_sdk['sources'].items()
        if name.startswith(('src/', 'include/'))
    }
    if before_engine != selected_sources:
        raise RuntimeError('Selector source snapshot must match the selected SDK inputs')
    instrument_engine(engine, escape)
    instrument_app(app_source, escape)
    env = dict(os.environ)
    native = Path(env['CONDA_PREFIX'])
    args = [
        '-S',
        app_source,
        '-B',
        output / 'cmake',
        '-G',
        'Ninja',
        '-DCMAKE_BUILD_TYPE=Release',
        '-DEDI_BUILD_APP=ON',
        '-DEDI_BUILD_BINDINGS=OFF',
    ]
    gui = root / 'build/app/_deps/gui_components-src'
    if gui.is_dir():
        args.append('-DFETCHCONTENT_SOURCE_DIR_GUI_COMPONENTS=' + str(gui))
    if backend == 'browser':
        command, env = browser_configuration(output, engine, native, args, env)
    else:
        prefix = output / 'crysta-prefix'
        run(
            [
                'cmake',
                '-S',
                engine,
                '-B',
                output / 'crysta',
                '-G',
                'Ninja',
                '-DCMAKE_BUILD_TYPE=Release',
                '-DCRYSTA_CXX_PACKAGE=ON',
                '-DCRYSTA_LTO=OFF',
                '-DCRYSTA_OPENMP=ON',
                '-DCMAKE_DISABLE_FIND_PACKAGE_doctest=ON',
                '-DCMAKE_INSTALL_PREFIX=' + str(prefix),
            ],
            env=env,
        )
        run(['cmake', '--build', output / 'crysta', '--target', 'crysta_core', '-j', '4'], env=env)
        # Install the actual engine's full SDK surface after the static observer is linked.
        run(['cmake', '--build', output / 'crysta', '-j', '4'], env=env)
        run(['cmake', '--install', output / 'crysta'], env=env)
        shutil.copytree(
            sdk / 'lib/crysta-runtime', prefix / 'lib/crysta-runtime', dirs_exist_ok=True
        )
        args.extend([
            '-Dcrysta_DIR=' + str(prefix / 'lib/cmake/crysta'),
            '-DCMAKE_PREFIX_PATH=' + str(prefix) + ';' + str(native),
            '-DCMAKE_CXX_COMPILER_LAUNCHER=ccache',
        ])
        command = ['cmake', *args]
    run(command, env=env)
    run(['cmake', '--build', output / 'cmake', '--target', 'edi_app', '-j', '4'], env=env)
    executable = output / 'cmake/app' / ('edi_app.wasm' if backend == 'browser' else 'edi_app')
    receipt = {
        'dependencies': shared_inputs,
        'backend': backend,
        'escape': escape,
        'production': production,
        'compiled_inputs': {'production': production, 'sdk': compiled_sdk},
        'source_sha': app_sha,
        'engine_sha': engine_sha,
        'engine_sources': before_engine,
        'sdk_manifest': manifest,
        'fixture': fixture_hashes,
        'executable': str(executable),
        'binary': hashlib.sha256(executable.read_bytes()).hexdigest(),
    }
    for copied in (engine, app_source):
        for name, digest in fixture_hashes.items():
            if (
                hashlib.sha256(
                    (copied / 'tests/fixtures/thread_selector' / name).read_bytes()
                ).hexdigest()
                != digest
            ):
                raise RuntimeError('The receipt must bind exactly the compiled fixture snapshot')
    if fixture_hashes != {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in HERE.iterdir() if p.is_file()
    }:
        raise RuntimeError('Selector fixture changed during its real build')
    validate_current_inputs(receipt, root, sdk, engine_source)
    validate_dependencies(receipt, 'selector', root)
    seal_bundle(receipt)
    (output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
    prepare_observations(output, receipt)
    validate_dependencies(receipt, 'selector', root)
    validate_bundle(receipt)


def prepare_observations(output, receipt):
    from tests.fixtures.thread_selector.harness import capture  # noqa: PLC0415

    validate_bundle(receipt)
    controls = {}
    for control in (None, *ESCAPES):
        scratch = output / 'captures' / (control or 'normal')
        scratch.mkdir(parents=True, exist_ok=True)
        controls[control or 'normal'] = capture(receipt, scratch, dict(os.environ), control)
    validate_bundle(receipt)
    observations = output / 'observations.json'
    observations.write_text(json.dumps({'receipt': receipt, 'controls': controls}) + '\n')
    receipt['observations_sha256'] = hashlib.sha256(observations.read_bytes()).hexdigest()
    (output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('root', 'output', 'sdk', 'engine-source'):
        parser.add_argument('--' + name, required=True, type=Path)
    parser.add_argument('--backend', choices=('desktop', 'browser'), required=True)
    parser.add_argument('--escape', choices=ESCAPES)
    args = parser.parse_args()
    build(
        args.root.resolve(),
        args.output.resolve(),
        args.sdk.resolve(),
        args.engine_source.resolve(),
        args.backend,
        args.escape,
    )
