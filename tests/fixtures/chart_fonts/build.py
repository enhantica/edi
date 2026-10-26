"""Build the same narrow Qt Quick font witness for Qt's browser kit."""

import argparse
import hashlib
import json
import os
import subprocess
import tarfile
from pathlib import Path

from tests.fixtures.app_environment.closure import dependencies
from tests.fixtures.scan_app.build_probe import fingerprint, sdk_inputs
from tests.fixtures.scan_screen.build import browser_configuration

ROOT = Path(__file__).resolve().parents[3]
FIXTURES = (
    'tests/fixtures/loop_parameter_ids/line-segment',
    'docs/user/cli/sc-neut-cwl_pr2nio4-5c2_fit/project',
    'tests/fixtures/report_evolution/project',
    'tests/fixtures/correlations/polynomial-3',
)
PROBES = (
    'tests/system/app/ChartFonts.qml',
    'tests/unit/app/test_chart_fonts.cpp',
    'app/tests/app_tests_main.cpp',
)


def write_changed(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.is_file() or path.read_bytes() != data:
        path.write_bytes(data)


def probe_inputs(root):
    paths = [root / name for name in PROBES]
    paths.extend(path for name in FIXTURES for path in (root / name).rglob('*') if path.is_file())
    paths.extend(Path(__file__).parent.glob('*.*'))
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(paths)
        if path.is_file()
    }


def build(output, sdk, engine_source):  # noqa: PLR0914 - distinct sealed build input channels
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    source = output / 'source'
    source.mkdir(exist_ok=True)
    production = fingerprint(ROOT)
    probes = probe_inputs(ROOT)
    inputs = sdk_inputs(sdk, engine_source)
    shared = dependencies('chart-fonts', ROOT)
    if not (source / 'CMakeLists.txt').is_file():
        archive = output / 'source.tar'
        with archive.open('wb') as stream:
            subprocess.run(['git', 'archive', 'HEAD'], cwd=ROOT, stdout=stream, check=True)
        with tarfile.open(archive) as stream:
            stream.extractall(source, filter='data')
    for relative in fingerprint(source).keys() - production.keys():
        (source / relative).unlink()
    # Bind actual working-tree production bytes too, including a pending shared theme.
    for relative in production.keys() | probes.keys():
        if relative in {'app/CMakeLists.txt', 'app/tests/app_tests_main.cpp'}:
            continue  # Write the final instrumented bytes once below; retain unchanged objects.
        destination = source / relative
        write_changed(destination, (ROOT / relative).read_bytes())
    main = source / 'app/tests/app_tests_main.cpp'
    text = (ROOT / 'app/tests/app_tests_main.cpp').read_text()
    if text.count('"offscreen"') != 1:
        raise RuntimeError(
            'The browser witness requires the unchanged native runner platform seam'
        )
    write_changed(main, text.replace('"offscreen"', '"wasm"').encode())
    cmake = source / 'app/CMakeLists.txt'
    recipe = (
        (ROOT / 'app/CMakeLists.txt').read_text()
        + """
qt_add_executable(chart_font_tests tests/app_tests_main.cpp
    ${PROJECT_SOURCE_DIR}/tests/unit/app/test_chart_fonts.cpp ${EDI_APP_BUILD_COMMIT_CPP})
add_dependencies(chart_font_tests edi_app_build_commit)
target_link_libraries(chart_font_tests PRIVATE edi_app_module edi_app_moduleplugin
    ${EDI_GUI_BASE_TARGETS} Qt6::QuickTest Qt6::QuickTestplugin)
target_link_options(chart_font_tests PRIVATE "SHELL:-s ASYNCIFY" "-Os")
target_compile_definitions(chart_font_tests PRIVATE
    QUICK_TEST_SOURCE_DIR=":/chart-fonts/tests/system/app" QT_HAVE_EMSCRIPTEN_ASYNCIFY)
set_target_properties(chart_font_tests PROPERTIES AUTOMOC ON)
set(font_probe ${PROJECT_SOURCE_DIR}/tests/system/app/ChartFonts.qml)
"""
    )
    for index, relative in enumerate(FIXTURES):
        recipe += (
            f'file(GLOB_RECURSE font_fixture_{index} LIST_DIRECTORIES false '
            f'"${{PROJECT_SOURCE_DIR}}/{relative}/*")\n'
        )
    recipe += (
        'qt_add_resources(chart_font_tests "font_inputs" PREFIX "/chart-fonts" '
        'BASE "${PROJECT_SOURCE_DIR}" FILES ${font_probe} '
    )
    recipe += ' '.join('${font_fixture_' + str(index) + '}' for index in range(len(FIXTURES)))
    recipe += ')\n'
    write_changed(cmake, recipe.encode())
    env = dict(os.environ)
    native = Path(env['CONDA_PREFIX'])
    args = [
        '-S',
        str(source),
        '-B',
        str(output / 'cmake'),
        '-G',
        'Ninja',
        '-DCMAKE_BUILD_TYPE=Release',
        '-DEDI_BUILD_APP=ON',
        '-DEDI_BUILD_BINDINGS=OFF',
    ]
    gui = ROOT / 'build/app/_deps/gui_components-src'
    if gui.is_dir():
        args.append('-DFETCHCONTENT_SOURCE_DIR_GUI_COMPONENTS=' + str(gui))
    command, env = browser_configuration(output, engine_source, native, args, env)
    subprocess.run(command, env=env, check=True)
    subprocess.run(
        ['cmake', '--build', str(output / 'cmake'), '--target', 'chart_font_tests', '-j', '4'],
        env=env,
        check=True,
    )
    if fingerprint(ROOT) != production or probe_inputs(ROOT) != probes:
        raise RuntimeError(
            'The chart-font build refuses production or probe inputs changed during compilation'
        )
    if sdk_inputs(sdk, engine_source) != inputs or dependencies('chart-fonts', ROOT) != shared:
        raise RuntimeError('The chart-font build refuses changed SDK or shared GUI recipe inputs')
    site = output / 'cmake/app'
    assets = {
        str(path.relative_to(site)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in site.rglob('*')
        if path.is_file()
    }
    receipt = {
        'production': production,
        'probes': probes,
        'sdk': inputs,
        'dependencies': shared,
        'site': str(site),
        'assets': assets,
        'backend': 'browser',
    }
    (output / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('output', 'sdk', 'engine-source'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    build(args.output, args.sdk, args.engine_source)
