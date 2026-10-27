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
    'docs/user/cli/sc-neut-cwl_pr2nio4-5c2/project',
    'tests/fixtures/report_evolution/project',
    'tests/fixtures/correlations/polynomial-3',
)
PROBES = (
    'tests/system/app/ChartFonts.qml',
    'tests/unit/app/test_chart_fonts.cpp',
    'tests/fixtures/scan_screen/build.py',
    'tests/fixtures/scan_screen/harness.py',
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
        if relative == 'app/CMakeLists.txt':
            continue  # Write the final instrumented bytes once below; retain unchanged objects.
        destination = source / relative
        write_changed(destination, (ROOT / relative).read_bytes())
    cmake = source / 'app/CMakeLists.txt'
    recipe = (
        (ROOT / 'app/CMakeLists.txt').read_text()
        + """
qt_add_executable(chart_font_tests ${PROJECT_SOURCE_DIR}/tests/fixtures/chart_fonts/main.cpp
    ${PROJECT_SOURCE_DIR}/tests/unit/app/test_chart_fonts.cpp ${EDI_APP_BUILD_COMMIT_CPP})
add_dependencies(chart_font_tests edi_app_build_commit)
target_link_libraries(chart_font_tests PRIVATE edi_app_module edi_app_moduleplugin
    ${EDI_GUI_BASE_TARGETS})
set_target_properties(chart_font_tests PROPERTIES AUTOMOC ON)
set(font_probe ${PROJECT_SOURCE_DIR}/tests/fixtures/chart_fonts/WebFonts.qml
    ${PROJECT_SOURCE_DIR}/tests/fixtures/chart_fonts/cases.json)
"""
    )
    for index, relative in enumerate(FIXTURES):
        recipe += (
            f'file(GLOB_RECURSE font_fixture_{index} LIST_DIRECTORIES false '
            f'"${{PROJECT_SOURCE_DIR}}/{relative}/*")\n'
        )
    # Qt's earlier example resources set persistent source-file aliases. Give this
    # separate fixture bundle its own explicit root-relative aliases.
    recipe += 'foreach(font_input IN LISTS font_probe '
    recipe += ' '.join('font_fixture_' + str(index) for index in range(len(FIXTURES)))
    recipe += ')\n'
    recipe += (
        'file(RELATIVE_PATH font_alias "${PROJECT_SOURCE_DIR}" "${font_input}")\n'
        'set_source_files_properties("${font_input}" PROPERTIES '
        'QT_RESOURCE_ALIAS "${font_alias}")\n'
        'endforeach()\n'
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
