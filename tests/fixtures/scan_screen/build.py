"""Build a passive observer into the committed app host, on desktop or a Qt web kit."""

from __future__ import annotations

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
from tests.fixtures.scan_app.build_probe import (
    fingerprint,
    fingerprint_headers,
    sdk_inputs,
    validate_current_inputs,
)


def run(command, **kwargs):
    subprocess.run(list(map(str, command)), check=True, **kwargs)


def follow_diagnostic(event):
    return """
    if (!follow_file_.empty()) {
        const auto* observed = currentExperiment();
        ::scan_screen_follow(QJsonObject{
            {"event", EVENT},
            {"file", QString::fromStdString(follow_file_)},
            {"token", static_cast<qint64>(follow_token_)},
            {"followIndex", follow_index_},
            {"currentIndex", current_dataset_},
            {"projectedIndex", projected_dataset_},
            {"patternShown", patternShown()},
            {"followBefore", static_cast<qint64>(follow_before_)},
            {"followGeneration", static_cast<qint64>(follow_generation_)},
            {"patternGeneration",
             static_cast<qint64>(observed ? observed->patternGeneration() : 0)},
            {"presentedGeneration",
             static_cast<qint64>(observed ? observed->presentedGeneration() : 0)},
            {"renderSwaps", render_swaps_},
            {"deadlineActive", render_wait_.isActive()},
            {"deadlineRemainingMs", render_wait_.remainingTime()}});
    }
""".replace('EVENT', event)


def worker_diagnostic(event, remaining='-1', file='record.file_name'):
    return (
        f'\nscan_screen_worker("{event}", {file}, '
        'self->frame_wanted.load(std::memory_order_acquire), '
        'self->wait_patterns.load(std::memory_order_acquire), token.cancelled(), '
        f'file_frame && file_frame->first == {file}, {remaining});\n'
    )


def observer_sources(source):
    changed = {}
    main = source / 'app/main.cpp'
    text = main.read_text()
    marker = '    edi_app::install_web_page_hooks(engine);'
    if text.count(marker) != 1:
        raise RuntimeError('The screen observer must bind the actual host after its QML load')
    changed['app/main.cpp'] = (
        'void scan_screen_install(class QQmlApplicationEngine&);\n'
        'void scan_screen_settings(class QQmlApplicationEngine&);\n'
        + text.replace(marker, '    scan_screen_install(engine);\n' + marker, 1).replace(
            '    edi_app::configure_engine(engine);',
            '    edi_app::configure_engine(engine);\n    scan_screen_settings(engine);',
            1,
        )
    )
    job = source / 'core/src/fit_job.cpp'
    text = job.read_text()
    matches = list(
        re.finditer(
            r'const\s+FileCompleteCallback\s+on_file_complete\s*=\s*\[[^]]*\]'
            r'\s*\(const\s+ScanFileRecord&\s+record\)\s*\{',
            text,
        )
    )
    if len(matches) != 1:
        raise RuntimeError('The screen observer must bind the real completed-file worker callback')
    marker = matches[0].group()
    text = text.replace(
        marker,
        marker.replace('&file_frame]', '&file_frame, &token]')
        + '\nscan_screen_completed(record.file_name);'
        + worker_diagnostic('worker-file-complete'),
        1,
    )
    for marker, replacement in (
        (
            '#if !EDI_WORKER_OWNER_THREAD\n                    if (self->wait_patterns',
            worker_diagnostic('worker-frame-emitted', file='file')
            + '#if !EDI_WORKER_OWNER_THREAD\n                    if (self->wait_patterns',
        ),
        (
            '                        std::unique_lock lock(self->shown_mutex);',
            worker_diagnostic(
                'worker-wait-begin',
                'std::chrono::duration_cast<std::chrono::milliseconds>('
                'deadline - std::chrono::steady_clock::now()).count()',
                file='file',
            )
            + '                        std::unique_lock lock(self->shown_mutex);',
        ),
        (
            (
                '                            self->shown.wait_for(lock, '
                'std::chrono::milliseconds(20));\n                        }'
            ),
            '                            self->shown.wait_for(lock, '
            'std::chrono::milliseconds(20));\n'
            '                        }'
            + worker_diagnostic(
                'worker-wait-end',
                'std::chrono::duration_cast<std::chrono::milliseconds>('
                'deadline - std::chrono::steady_clock::now()).count()',
                file='file',
            ),
        ),
    ):
        if text.count(marker) != 1:
            raise RuntimeError('The screen diagnostics must bind each real worker wait once')
        text = text.replace(marker, replacement, 1)
    changed['core/src/fit_job.cpp'] = (
        '#include <string>\nvoid scan_screen_completed(const std::string&);\n'
        'void scan_screen_worker(const char*, const std::string&, bool, bool, bool, bool, long);\n'
        + text
    )
    text = (source / 'app/src/project_view_model.cpp').read_text()
    for marker, replacement in (
        (
            '[this] { followRendered(false); }',
            '[this] {' + follow_diagnostic('"render-timeout"') + ' followRendered(false); }',
        ),
        (
            '    render_wait_.start(kRenderWaitMs);\n}',
            '    render_wait_.start(kRenderWaitMs);\n' + follow_diagnostic('"handover"') + '}',
        ),
        (
            '    if (window == nullptr || !presentedFollowed()) {',
            follow_diagnostic('"await-render"')
            + '    if (window == nullptr || !presentedFollowed()) {',
        ),
        (
            '    render_wait_.start(kRenderWaitMs);\n    window->update();',
            '    render_wait_.start(kRenderWaitMs);\n'
            + follow_diagnostic('"render-wait-armed"')
            + '    window->update();',
        ),
        (
            '    const std::string file = std::move(follow_file_);',
            follow_diagnostic('drawn ? "release-drawn" : "release-undrawn"')
            + '    const std::string file = std::move(follow_file_);',
        ),
    ):
        if text.count(marker) != 1:
            raise RuntimeError('The screen diagnostics must bind each real handover/deadline once')
        text = text.replace(marker, replacement, 1)
    changed['app/src/project_view_model.cpp'] = (
        '#include <QJsonObject>\nvoid scan_screen_follow(const QJsonObject&);\n' + text
    )
    cmake = source / 'app/CMakeLists.txt'
    changed['app/CMakeLists.txt'] = (
        cmake.read_text() + '\ntarget_sources(edi_app PRIVATE '
        '${PROJECT_SOURCE_DIR}/tests/fixtures/scan_screen/observe.cpp)\n'
    )
    return changed


def snapshot(root, output, fixture):
    source = output / 'source'
    source.mkdir(exist_ok=True)
    source_sha = subprocess.check_output(
        ['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True
    ).strip()
    (output / 'source-sha.txt').write_text(source_sha + '\n')
    archive = output / 'source.tar'
    with archive.open('wb') as stream:
        run(['git', '-C', root, 'archive', source_sha], stdout=stream)
    with tarfile.open(archive) as stream:
        stream.extractall(source, filter='data')
    production = fingerprint(source)
    shutil.copytree(fixture, source / 'tests/fixtures/scan_screen', dirs_exist_ok=True)
    for relative, text in observer_sources(source).items():
        (source / relative).write_text(text)
    return source, production


def browser_configuration(output, engine_source, native, args, env):
    toolchain = Path(env.get('EDI_WASM_TOOLCHAIN', str(Path.home() / '.cache/edi-wasm')))
    emsdk = toolchain / 'emsdk-4.0.7'
    env = json.loads(
        subprocess.check_output(
            [
                'bash',
                '-c',
                (
                    'source "$1/emsdk_env.sh" >/dev/null 2>&1; '
                    'python -c "import os,json; print(json.dumps(dict(os.environ)))"'
                ),
                'scan-screen',
                str(emsdk),
            ],
            env=env,
            text=True,
        )
    )
    for key in (
        'CC',
        'CXX',
        'CFLAGS',
        'CXXFLAGS',
        'CPPFLAGS',
        'LDFLAGS',
        'CONDA_PREFIX',
        'CMAKE_CXX_COMPILER_LAUNCHER',
        'CMAKE_C_COMPILER_LAUNCHER',
    ):
        env.pop(key, None)
    env['EM_COMPILER_WRAPPER'] = 'ccache'
    prefix = output / 'crysta-prefix'
    run(
        [
            'emcmake',
            'cmake',
            '-S',
            engine_source,
            '-B',
            output / 'crysta',
            '-G',
            'Ninja',
            '-DCMAKE_BUILD_TYPE=Release',
            '-DCRYSTA_CXX_PACKAGE=ON',
            '-DCRYSTA_WASM_THREADS=ON',
            '-DCRYSTA_WASM_SIMD=ON',
            '-DCRYSTA_SLEEF=ON',
            '-DCRYSTA_REQUIRE_SIMD=ON',
            '-DCRYSTA_OPENMP=OFF',
            '-DCRYSTA_EIGEN_FETCH=ON',
            '-DCMAKE_DISABLE_FIND_PACKAGE_doctest=ON',
            '-DCMAKE_INSTALL_PREFIX=' + str(prefix),
        ],
        env=env,
    )
    run(['cmake', '--build', output / 'crysta', '-j', '4'], env=env)
    run(['cmake', '--install', output / 'crysta'], env=env)
    args.extend([
        '-Dcrysta_DIR=' + str(prefix / 'lib/cmake/crysta'),
        '-DEigen3_DIR=' + str(toolchain / 'eigen-3.4.0/share/eigen3/cmake'),
        '-DQT_HOST_PATH=' + str(native),
        '-DQT_HOST_PATH_CMAKE_DIR=' + str(native / 'lib/cmake'),
        '-DEDI_WORKER_OWNER_THREAD=OFF',
        '-DQT_WASM_PTHREAD_POOL_SIZE=8',
    ])
    command = ['sh', toolchain / 'qt/6.11.2/wasm_multithread/bin/qt-cmake', *args]
    return command, env


def build(root, output, sdk, engine_source, backend):  # noqa: PLR0914 - qualified build inputs
    root, output, sdk, engine_source = map(Path.resolve, (root, output, sdk, engine_source))
    output.mkdir(parents=True, exist_ok=True)
    shared_inputs = dependencies('screen', root)
    compiled_sdk = sdk_inputs(sdk, engine_source)
    fixture = Path(__file__).resolve().parent
    fixture_hashes = {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in fixture.iterdir()
        if p.is_file()
    }
    source, production = snapshot(root, output, fixture)
    env = dict(os.environ)
    native = Path(env['CONDA_PREFIX'])
    args = [
        '-S',
        source,
        '-B',
        output / 'cmake',
        '-G',
        'Ninja',
        '-DCMAKE_BUILD_TYPE=Release',
        '-DEDI_BUILD_APP=ON',
        '-DEDI_BUILD_BINDINGS=OFF',
    ]
    if (root / 'build/app/_deps/gui_components-src').is_dir():
        args.append(
            '-DFETCHCONTENT_SOURCE_DIR_GUI_COMPONENTS='
            + str(root / 'build/app/_deps/gui_components-src')
        )
    if backend == 'desktop':
        args.extend([
            '-Dcrysta_DIR=' + str(sdk / 'lib/cmake/crysta'),
            '-DCMAKE_PREFIX_PATH=' + str(sdk) + ';' + str(native),
            '-DCMAKE_CXX_COMPILER_LAUNCHER=ccache',
        ])
        command = ['cmake', *args]
    else:
        command, env = browser_configuration(output, engine_source, native, args, env)
    run(command, env=env)
    run(['cmake', '--build', output / 'cmake', '--target', 'edi_app', '-j', '4'], env=env)
    executable = output / 'cmake/app' / ('edi_app' if backend == 'desktop' else 'edi_app.wasm')
    receipt = {
        'dependencies': shared_inputs,
        'backend': backend,
        'production': production,
        'compiled_inputs': {'production': production, 'sdk': compiled_sdk},
        'source_sha': (output / 'source-sha.txt').read_text().strip(),
        'engine_sha': subprocess.check_output(
            ['git', '-C', engine_source, 'rev-parse', 'HEAD'], text=True
        ).strip(),
        'sdk_headers': fingerprint_headers(sdk / 'include'),
        'sdk_manifest': json.loads((sdk / 'share/crysta-sdk/manifest.json').read_text()),
        'binary': hashlib.sha256(executable.read_bytes()).hexdigest(),
        'executable': str(executable),
        'fixture': fixture_hashes,
    }
    for name, digest in fixture_hashes.items():
        if (
            hashlib.sha256((source / 'tests/fixtures/scan_screen' / name).read_bytes()).hexdigest()
            != digest
        ):
            raise RuntimeError('Screen receipt requires its actual compiled fixture snapshot')
    validate_current_inputs(receipt, root, sdk, engine_source)
    validate_dependencies(receipt, 'screen', root)
    seal_bundle(receipt)
    (output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')


def refresh(root, output, sdk, engine_source):
    record_path = output / 'receipt.json'
    receipt = json.loads(record_path.read_text())
    validate_dependencies(receipt, 'screen', root)
    validate_bundle(receipt)
    validate_current_inputs(receipt, root, sdk, engine_source)
    if receipt['production'] != fingerprint(root):
        raise RuntimeError('A screen observer refresh refuses changed production sources')
    source = output / 'source'
    for relative, digest in receipt['production'].items():
        if (
            relative not in {'app/main.cpp', 'core/src/fit_job.cpp', 'app/CMakeLists.txt'}
            and hashlib.sha256((source / relative).read_bytes()).hexdigest() != digest
        ):
            raise RuntimeError('A screen observer refresh refuses a changed private source')
    for relative, text in observer_sources(root).items():
        if (source / relative).read_text() != text:
            raise RuntimeError(
                'A screen observer refresh refuses changed host or worker instrumentation'
            )
    fixture = Path(__file__).resolve().parent
    for name, digest in receipt['fixture'].items():
        if (
            name != 'observe.cpp'
            and hashlib.sha256((fixture / name).read_bytes()).hexdigest() != digest
        ):
            raise RuntimeError('Screen refresh refuses a changed build or driver input')
    shutil.copyfile(fixture / 'observe.cpp', source / 'tests/fixtures/scan_screen/observe.cpp')
    run(['cmake', '--build', output / 'cmake', '--target', 'edi_app', '-j', '4'])
    receipt['binary'] = hashlib.sha256(Path(receipt['executable']).read_bytes()).hexdigest()
    receipt['fixture'] = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in fixture.iterdir()
        if path.is_file()
    }
    validate_current_inputs(receipt, root, sdk, engine_source)
    seal_bundle(receipt)
    record_path.write_text(json.dumps(receipt, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    for name in ('root', 'output', 'sdk', 'engine-source'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--backend', choices=('desktop', 'browser'), required=True)
    parser.add_argument('--refresh', action='store_true')
    args = parser.parse_args()
    if args.refresh:
        refresh(args.root.resolve(), args.output.resolve(), args.sdk, args.engine_source)
    else:
        build(args.root, args.output, args.sdk, args.engine_source, args.backend)
