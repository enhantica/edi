"""Scan integration seams from the saved-file contract and owner records."""

from __future__ import annotations

import fnmatch
import hashlib
import json
import re
import shlex
import subprocess
from pathlib import Path

import pytest
import yaml

from tests.integration.py.test_scan_app_contract import (
    APP,
    ROOT,
    block,
    evaluate,
    item,
    javascript,
    property_value,
    require,
    source,
    spans,
)


def test_scan_worker_routes_both_modes_to_existing_driver(tmp_path):
    text = re.sub(
        r'//[^\n]*|/\*.*?\*/', '', (ROOT / 'core/src/fit_job.cpp').read_text(), flags=re.DOTALL
    )
    assert worker_dispatch(text, tmp_path) == [
        'sequential:11:22:33:44',
        'independent:11:22:33:44',
    ], 'Scan worker wiring: each selected mode forwards every subscriber to its own driver'


def test_scan_availability_and_joint_mode_follow_scan_declaration(tmp_path):
    model = source('src/analysis_view_model.cpp')
    # Observe the option producer consumed by the actual mode selector.
    require(
        source('qml/Pages/Analysis/FittingModeGroup.qml'),
        r'options:\s*row\.analysis\s*\?\s*row\.analysis\.fittingModeOptions',
        'Scan mode wiring: the actual picker uses the guarded options model',
    )
    assert joint_options(model, tmp_path) == ['1', '0', '1'], (
        'Scan mode wiring: joint availability follows declaration in both '
        'directions in the consumed options producer'
    )


def test_scan_stop_continue_and_follow_have_model_state(tmp_path):
    assert selection_follow(source('src/project_view_model.cpp'), tmp_path) == [
        '0:2',
        '1:1',
        '1:1',
    ], (
        'Follow wiring: the actual changed manual-selection path disables '
        'Follow and invalid or unchanged choices retain it'
    )
    assert fit_state(
        source('src/fit_view_model.hpp'), source('src/fit_view_model.cpp'), tmp_path
    ) == ['0:0', '1:0', '0:1'], (
        'Scan state wiring: the consumed getters distinguish idle, '
        'running scan and stopped continuation'
    )


def test_empty_selectors_are_hidden_on_experiment_and_structure_pages():
    workflow = source('qml/Components/WorkflowPage.qml')
    selector = block(workflow, 'MainAreaBlockSelector {')
    assert (
        property_value(selector, 'visible')
        == 'page.blockSelectorShown && page.blocks !== null && page.bloc'
        'ks.count > 0'
    ), 'Selector wiring: the actual main-area selector hides for an empty bound model'
    for page, model in [('Experiment', 'experiments'), ('Structure', 'structures')]:
        text = source(f'qml/Pages/{page}/{page}Page.qml')
        require(
            text,
            r'blocks:\s*project \? project\.' + model + r' : null',
            'Selector wiring: each page supplies its own project-item model',
        )


def test_selector_moves_to_main_tab_bar_once():
    workflow = source('qml/Components/WorkflowPage.qml')
    main = block(workflow, 'mainView:')
    assert main.count('MainAreaBlockSelector {') == 1, (
        'Selector wiring: the main view owns one placement component'
    )
    sidebar = block(workflow, 'sideBar:')
    assert 'BlockSelector' not in sidebar, (
        'Selector wiring: no selector instance remains in the sidebar'
    )
    placement = source('qml/Components/MainAreaBlockSelector.qml')
    assert placement.count('BlockSelector {') == 1, (
        'Selector wiring: placement composes exactly one original selector'
    )
    child = block(placement, 'BlockSelector {')
    assert property_value(child, 'width') == 'placement.width', (
        'Selector wiring: the actual selector follows main-area width'
    )
    for page in ('Experiment', 'Structure', 'Analysis'):
        text = source(f'qml/Pages/{page}/{page}Page.qml')
        assert not re.search(r'\b(?:BlockSelector|MainAreaBlockSelector)\s*\{', text), (
            'Selector wiring: pages use the workflow selector rather than duplicate it'
        )

    selector = block(source('qml/Components/WorkflowPage.qml'), 'MainAreaBlockSelector {')
    for name in ('blocks', 'blockIndex', 'blocksTextRole'):
        assert property_value(selector, name) == 'page.' + name, (
            'Selector wiring: the placed child receives the page model and selection'
        )
        require(
            placement,
            r'property alias ' + name + r': selector\.' + name + r'\s*(?:\n|$)',
            'Selector wiring: placement forwards its exposed model and index '
            'to the original child',
        )
    assert property_value(selector, 'onBlockActivated') == 'index => page.blockActivated(index)', (
        'Selector wiring: the placed child returns the actual activated index'
    )
    assert (
        property_value(child, 'onBlockActivated') == 'index => placement.blockActivated(index)'
    ), 'Selector wiring: activation crosses placement without changing its index'
    original = source('qml/Components/BlockSelector.qml')
    picker = block(original, 'SearchableComboBox {')
    assert (
        property_value(picker, 'model') == 'blocks'
        and property_value(picker, 'currentIndex') == 'blockIndex'
    ), 'Selector wiring: the actual picker consumes the forwarded blocks and current index'
    handler = property_value(picker, 'onActivated')
    result = javascript(
        'const Qt={binding:f=>f()};let picked=[];const '
        'row={blockActivated:i=>picked.push(i)};const '
        'selector={blockIndex:3,currentIndex:0};('
        + handler
        + ')(17);console.log(JSON.stringify([picked,selector.currentInd'
        'ex]));'
    )
    assert result == [[17], 3], (
        'Selector wiring: activation retains the source index and rebinds the shared selection'
    )
    for page, kind in [
        ('Experiment', 'Experiment'),
        ('Analysis', 'Experiment'),
        ('Structure', 'Structure'),
    ]:
        text = source(f'qml/Pages/{page}/{page}Page.qml')
        assert (
            property_value(text, 'blockIndex') == 'project ? project.current' + kind + 'Index : -1'
        ), 'Selector wiring: each page follows its shared project index'
        assert (
            property_value(text, 'onBlockActivated')
            == 'index => page.project.current' + kind + 'Index = index'
        ), 'Selector wiring: each page forwards the activated index to the same project selection'


def test_scan_explorer_header_has_declared_columns_in_order():
    header = block(source('qml/Pages/Experiment/ExperimentsGroup.qml'), 'header:')
    labels = re.findall(r'text:\s*qsTr\("([^\"]+)"\)', header)
    assert labels[:4] == ['No.', 'Fit', 'Datablock', 'File'], (
        'Dataset list labels: scan columns appear in number, fit, datablock, file order'
    )
    repeater = block(header, 'Repeater {')
    table = block(source('qml/Pages/Experiment/ExperimentsGroup.qml'), 'EaComponents.TableView {')
    table_id = property_value(table, 'id')
    assert property_value(repeater, 'model') == table_id + '.model.extractColumns', (
        'Dataset list wiring: the displayed header consumes extract '
        'columns from its actual table model'
    )


def evolution_component():
    page = source('qml/Pages/Analysis/AnalysisPage.qml')
    items = re.search(r'mainItems:\s*\[([\s\S]*?)\n\s*\]', page)
    assert items, 'Evolution wiring: the analysis main view declares its tab content'
    components = re.findall(r'(?m)^\s*(\w+)\s*\{', items.group(1))
    assert len(components) >= 2, (
        'Evolution wiring: the second main-view tab has its own actual content'
    )
    paths = list((APP / 'qml').rglob(components[1] + '.qml'))
    assert len(paths) == 1, 'Evolution wiring: the second content component resolves uniquely'
    return source(paths[0].relative_to(APP))


def assert_evolution_bindings(qml):
    candidates = []
    for begin, end in spans(qml):
        child = qml[begin:end]
        try:
            error = next(
                property_value(child, name)
                for name in ('errors', 'uncertainty', 'errorBars')
                if re.search(r'(?m)^\s*' + name + ':', child)
            )
            coordinates = next(
                property_value(child, name)
                for name in ('xValues', 'xAxis', 'axisMode')
                if re.search(r'(?m)^\s*' + name + ':', child)
            )
            handler = next(
                property_value(child, name)
                for name in ('onPointActivated', 'onClicked')
                if re.search(r'(?m)^\s*' + name + ':', child)
            )
            model = property_value(child, 'model')
        except (StopIteration, pytest.fail.Exception):
            continue
        candidates.append((child, error, coordinates, handler, model))
    assert len(candidates) == 1, (
        'Evolution wiring: one actual plotting consumer binds rows, '
        'errors, coordinates and its point event'
    )
    _child, error, coordinates, handler, model = candidates[0]
    require(
        model,
        r'^\w+\.\w+\.(?:points|series|rows)$',
        'Evolution wiring: the rendered series consumes the resolved result rows',
    )
    container = model.rsplit('.', 1)[0]
    assert coordinates.startswith(container + '.'), (
        'Evolution wiring: coordinates come from the same results object as the point series'
    )
    require(
        error,
        r'^(?:model|points|series)\.(?:uncertainty|errors)$',
        'Evolution wiring: errors read the rendered point uncertainty role',
    )
    require(
        handler,
        r'^(?:index|point)\s*=>\s*'
        + re.escape(container)
        + r'\.selectDataset\((?:index|point\.index)\)$',
        'Evolution wiring: the rendered point event selects its own result index',
    )
    root, field = container.split('.')
    context = (
        'let calls=[];const '
        + root
        + '={'
        + field
        + ':{xValues:[2,4,6],xAxis:[2,4,6],axisMode:"temperature",selec'
        'tDataset:i=>calls.push(i)}};const '
        'model={uncertainty:0.37,errors:0.37};const points=model;const '
        'series=model;'
    )
    assert evaluate(error, context) == 0.37, (
        'Evolution wiring: effective point uncertainty reaches the error binding'
    )
    assert evaluate(coordinates, context) in ([2, 4, 6], 'temperature'), (
        'Evolution wiring: effective coordinates read the switchable result axis'
    )
    argument = '{index:17}' if handler.startswith('point') else '17'
    program = context + ';(' + handler + ')(' + argument + ');console.log(JSON.stringify(calls));'
    assert javascript(program) == [17], (
        'Evolution wiring: the effective series event forwards the clicked point index'
    )


def test_parameter_evolution_connects_rendered_errors_axis_and_point_selection():
    assert_evolution_bindings(evolution_component())


def assert_stale_marker(consumer, results=None):
    if results is None:
        model = re.search(r'(?m)^\s*model:\s*(\w+\.\w+)\.(?:points|series|rows)\s*$', consumer)
        results = model.group(1) if model else 'bar.fit'
    markers = []
    for begin, end in spans(consumer):
        child = consumer[begin:end]
        try:
            text = property_value(child, 'text')
            if 'out of date' not in text:
                continue
            visible = property_value(child, 'visible')
        except pytest.fail.Exception:
            continue
        markers.append((text, visible))
    assert markers, 'Stale-result wiring: each results consumer has its own guarded marker'
    for text, visible in markers:
        match = re.fullmatch(r'(\w+)\.(\w+)\.(outOfDate|stale)', visible)
        if not match:
            continue
        root, field, flag = match.groups()
        assert root + '.' + field == results, (
            'Stale-result wiring: the marker reads the same result object '
            'that its consumer renders'
        )
        assert evaluate(text, 'const qsTr=x=>x;') == 'out of date', (
            'Stale-result wiring: the guarded actual marker displays the required text'
        )
        for stale in (False, True):
            context = (
                'const ' + root + '={' + field + ':{' + flag + ':' + str(stale).lower() + '}};'
            )
            assert evaluate(visible, context) == stale, (
                'Stale-result wiring: the marker is shown exactly for stale results'
            )
        return
    pytest.fail('Stale-result wiring: the results stale state must guard that actual marker')


def test_old_scan_results_are_retained_with_out_of_date_state():
    assert_stale_marker(item(source('qml/Components/StatusBar.qml'), 'statusBar.fit'))
    assert_stale_marker(evolution_component())


def test_bundled_project_load_and_save_as_use_the_writable_copy_routes():
    session = source('src/session.cpp')
    loader = block(session, 'bool Session::openExample(')
    require(
        loader,
        r'extracted_ = std::make_unique<QTemporaryDir>\(\)',
        'Working-copy wiring: the actual example loader allocates its temporary directory',
    )
    require(
        loader,
        r'const QString target = extracted_->filePath\(',
        'Working-copy wiring: the copied project is under that temporary directory',
    )
    require(
        loader,
        r'QFile::copy\(file, destination\)',
        'Working-copy wiring: the loader copies each resource file into the opened project',
    )
    require(
        loader,
        r'QFile::setPermissions\(destination, QFile::ReadOwner \| QFile::WriteOwner\)',
        'Working-copy wiring: the actual copied files are writable',
    )
    require(
        loader,
        r'return open\(target, exampleId\)',
        'Working-copy wiring: the opened project is the copied target',
    )
    require(
        loader,
        r'const QString destination = target \+ file\.mid\(source\.size\(\)\);',
        'Working-copy wiring: each copied destination preserves the path '
        'beneath the opened target',
    )
    saver = block(session, 'bool Session::saveAs(')
    require(
        saver,
        r'project_->saveTo\(directory\.toLocalFile\(\)\)',
        'Save As wiring: the actual action saves the current working project',
    )
    model = block(source('src/project_view_model.cpp'), 'QString ProjectViewModel::saveTo(')
    require(
        model,
        r'edi::save_project_as\(\*project_, directory\.toStdString\(\)\)',
        'Save As wiring: the action reaches the core project writer',
    )


def example_inventory(count):
    project_id = f'pd-neut-cwl_cosio-d20_scan-{count}f'
    base = ROOT / 'docs/user/cli' / project_id
    assert base.is_dir(), 'Examples: both selected scan projects must exist in the CLI plane'
    declaration = dict(
        shlex.split(line)
        for line in (base / 'project/analysis/analysis.edi').read_text().splitlines()
        if line.startswith('_sequential_fit.') and len(shlex.split(line)) == 2
    )
    directory = declaration['_sequential_fit.data_dir']
    pattern = declaration['_sequential_fit.file_pattern']
    return {
        file.name: hashlib.sha256(file.read_bytes()).hexdigest()
        for file in (base / 'project' / directory).iterdir()
        if file.is_file() and fnmatch.fnmatchcase(file.name, pattern)
    }


def assert_source_inventory(actual, count):
    corpus = json.loads((ROOT / 'tests/fixtures/c11_t62/scan-inputs.json').read_text())['files']
    expected = {
        Path(name).name: digest
        for name, digest in corpus.items()
        if name.startswith('experiments/d20_scan/')
        and (count == 324 or Path(name).name.startswith('01_'))
    }
    assert len(expected) == count, (
        'Examples: the independent frozen source corpus must contain the selected run'
    )
    assert actual == expected, (
        'Examples: every declared scan filename must match its frozen source checksum'
    )


@pytest.mark.parametrize('count', [162, 324])
def test_scan_examples_have_exact_source_file_inventory_and_checksums(count):
    assert_source_inventory(example_inventory(count), count)
    project_id = f'pd-neut-cwl_cosio-d20_scan-{count}f'
    registry = yaml.safe_load((ROOT / 'docs/user/cli/projects.yml').read_text())['projects']
    assert any(row['id'] == project_id for row in registry), (
        'Examples: the registry must expose each selected scan'
    )


@pytest.mark.parametrize('count', [162, 324])
def test_example_gate_rejects_swapped_names_with_matching_local_provenance(count):
    corpus = json.loads((ROOT / 'tests/fixtures/c11_t62/scan-inputs.json').read_text())['files']
    inventory = {
        Path(name).name: digest
        for name, digest in corpus.items()
        if name.startswith('experiments/d20_scan/')
        and (count == 324 or Path(name).name.startswith('01_'))
    }
    names = sorted(inventory)
    inventory[names[0]], inventory[names[1]] = inventory[names[1]], inventory[names[0]]
    with pytest.raises(AssertionError, match='frozen source checksum'):
        assert_source_inventory(inventory, count)


def resource_inventory(tmp_path, web, production=None):
    cmake = production if production is not None else (APP / 'CMakeLists.txt').read_text()
    body = cmake
    scratch = tmp_path / ('web' if web else 'desktop')
    scratch.mkdir(parents=True)
    receipt = scratch / 'inventory.tsv'
    harness = f"""cmake_minimum_required(VERSION 3.25)
project(ResourceProbe NONE)
set(PROJECT_SOURCE_DIR "{ROOT.as_posix()}")
set(CMAKE_CURRENT_SOURCE_DIR "{APP.as_posix()}")
set(EMSCRIPTEN {'TRUE' if web else 'FALSE'})
file(WRITE "{receipt.as_posix()}" "")
foreach(command include configure_file qt_add_library
 qt_add_qml_module target_include_directories set_target_properties
 qt_add_executable target_compile_definitions add_custom_target add_dependencies
 target_link_options install)
 function(${{command}})
 endfunction()
endforeach()
function(target_link_libraries target)
 set_property(GLOBAL APPEND PROPERTY "probe_links_${{target}}" ${{ARGN}})
endfunction()
function(qt_add_resources target resource)
 cmake_parse_arguments(ARG "" "PREFIX;BASE" "FILES;OPTIONS" ${{ARGN}})
 foreach(file IN LISTS ARG_FILES)
  get_filename_component(base "${{ARG_BASE}}" ABSOLUTE
   BASE_DIR "${{CMAKE_CURRENT_SOURCE_DIR}}")
  get_filename_component(absolute "${{file}}" ABSOLUTE
   BASE_DIR "${{CMAKE_CURRENT_SOURCE_DIR}}")
  file(RELATIVE_PATH relative "${{base}}" "${{absolute}}")
  get_source_file_property(alias "${{absolute}}" QT_RESOURCE_ALIAS)
  if(alias)
   set(relative "${{alias}}")
  endif()
  file(SHA256 "${{absolute}}" digest)
  set(row "${{target}}\\t${{resource}}\\t${{ARG_PREFIX}}/${{relative}}")
  file(APPEND "{receipt.as_posix()}" "${{row}}\\t${{digest}}\\n")
 endforeach()
endfunction()
{body}
set(queue edi_app)
set(reachable)
while(queue)
 list(POP_FRONT queue target)
 if(target IN_LIST reachable)
  continue()
 endif()
 list(APPEND reachable "${{target}}")
 get_property(edges GLOBAL PROPERTY "probe_links_${{target}}")
 list(APPEND queue ${{edges}})
endwhile()
list(JOIN reachable "\\n" target_text)
file(WRITE "{(scratch / 'targets.txt').as_posix()}" "${{target_text}}\\n")
"""
    (scratch / 'CMakeLists.txt').write_text(harness)
    result = subprocess.run(
        ['cmake', '-S', str(scratch), '-B', str(scratch / 'build')],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert result.returncode == 0, (
        'Examples: production resource configuration must execute: '
        + result.stdout
        + result.stderr
    )
    reachable = set((scratch / 'targets.txt').read_text().splitlines())
    effective = [
        line for line in receipt.read_text().splitlines() if line.split('\t')[0] in reachable
    ]
    return effective, (scratch / 'build/examples/index.txt').read_text().splitlines()


def bundled_inputs(files, project_id):
    records = [line.split('\t') for line in files]
    paths = [
        address
        for _target, _resource, address, _digest in records
        if address.startswith('/edi/examples/' + project_id + '/')
    ]
    assert len(paths) == len(set(paths)), (
        'Examples: each effective resource address has exactly one payload'
    )
    return {
        address: digest
        for target, _resource, address, digest in records
        if address.startswith('/edi/examples/' + project_id + '/')
    }


def assert_bundled_index(files, index):
    digest = hashlib.sha256(('\n'.join(index) + '\n').encode()).hexdigest()
    records = [line.split('\t') for line in files]
    assert any(
        address == '/edi/examples/index.txt' and actual == digest
        for target, _resource, address, actual in records
    ), 'Examples: the advertised index bytes are bundled at the address the loader opens'


def assert_web_exclusion(files, index):
    full = 'pd-neut-cwl_cosio-d20_scan-324f'
    corpus = json.loads((ROOT / 'tests/fixtures/c11_t62/scan-inputs.json').read_text())['files']
    full_hashes = {
        digest for name, digest in corpus.items() if name.startswith('experiments/d20_scan/')
    }
    assert full not in index and not any(full in line.split('\t')[2] for line in files), (
        'Examples: the full scan has no resource address on web under any label or target'
    )
    # Cooling shares the first run's bytes. Anything outside its approved addresses is excluded.
    assert not any(
        line.split('\t')[3] in full_hashes
        and not line.split('\t')[2].startswith('/edi/examples/pd-neut-cwl_cosio-d20_scan-162f/')
        for line in files
    ), 'Examples: full-scan data cannot be rebundled under another label, path or target on web'


def expected_bundle(count):
    project_id = f'pd-neut-cwl_cosio-d20_scan-{count}f'
    base = ROOT / 'docs/user/cli' / project_id / 'project'
    declaration = dict(
        shlex.split(line)
        for line in (base / 'analysis/analysis.edi').read_text().splitlines()
        if line.startswith('_sequential_fit.') and len(shlex.split(line)) == 2
    )
    inventory = example_inventory(count)
    assert_source_inventory(inventory, count)
    directory = declaration['_sequential_fit.data_dir']
    expected = {
        f'/edi/examples/{project_id}/project/{directory}/{name}': digest
        for name, digest in inventory.items()
    }
    metadata = sorted(base.rglob('*.edi'))
    assert (base / 'project.edi') in metadata and (base / 'analysis/analysis.edi') in metadata, (
        'Examples: each project supplies opening metadata'
    )
    assert any('/experiments/' in str(file) for file in metadata) and any(
        '/structures/' in str(file) for file in metadata
    ), 'Examples: each opening project carries its experiment and structure blocks'
    expected.update({
        f'/edi/examples/{project_id}/project/{file.relative_to(base).as_posix()}': hashlib.sha256(
            file.read_bytes()
        ).hexdigest()
        for file in metadata
    })
    return expected


@pytest.mark.parametrize('web', [False, True], ids=['desktop', 'web'])
def test_effective_bundle_contains_selected_scan_payloads(tmp_path, web):
    files, index = resource_inventory(tmp_path, web)
    assert_bundled_index(files, index)
    small = 'pd-neut-cwl_cosio-d20_scan-162f'
    large = 'pd-neut-cwl_cosio-d20_scan-324f'
    assert small in index, 'Examples: the cooling run must be offered in desktop and web'
    assert bundled_inputs(files, small) == expected_bundle(162), (
        'Examples: cooling resources bind every input path to its frozen source bytes'
    )
    if web:
        assert_web_exclusion(files, index)
    else:
        assert large in index and bundled_inputs(files, large) == expected_bundle(324), (
            'Examples: desktop bundles the full scan with the correct input paths and bytes'
        )


def test_resource_observer_rejects_comment_only_and_inactive_bundle_calls(tmp_path):
    cmake = (APP / 'CMakeLists.txt').read_text()
    live = cmake.replace('if(EXISTS ${project}/analysis/analysis.edi)', 'if(FALSE)')
    # The retained full scan is available before the smaller example is authored.
    good, _index = resource_inventory(tmp_path / 'good', False, live)
    full = 'pd-neut-cwl_cosio-d20_scan-324f'
    expected = expected_bundle(324)
    assert bundled_inputs(good, full) == expected, (
        'Examples: the control must reach the live full-scan resource inventory'
    )
    call = 'edi_app_bundle_examples(${_cli} ${EDI_APP_EXAMPLE_IDS})'
    for label, replacement in [
        ('comment', '# ' + call),
        ('inactive', 'if(FALSE)\n' + call + '\nendif()'),
    ]:
        mutated = live.replace(call, replacement)
        assert mutated != live, (
            'Examples: the packaging escape must alter the effective production call'
        )
        bad, _index = resource_inventory(tmp_path / label, False, mutated)
        assert bundled_inputs(bad, full) != expected, (
            'Examples: comments or inactive branches cannot stand for bundled payloads'
        )


@pytest.mark.parametrize('dimension', ['prefix', 'target', 'metadata', 'alias', 'index', 'hidden'])
def test_resource_observer_rejects_wrong_prefix_target_metadata_index_and_hidden_web_payload(
    tmp_path, dimension
):
    cmake = (
        (APP / 'CMakeLists.txt')
        .read_text()
        .replace('if(EXISTS ${project}/analysis/analysis.edi)', 'if(FALSE)')
    )
    full = 'pd-neut-cwl_cosio-d20_scan-324f'
    expected = expected_bundle(324)
    good, index = resource_inventory(tmp_path / 'good', False, cmake)
    assert bundled_inputs(good, full) == expected, (
        'Examples: the escape baseline carries every opening resource'
    )
    assert_bundled_index(good, index)
    for label, mutated in [
        (
            'alias',
            cmake.replace(
                'edi_app_bundle_examples(${_cli} ${EDI_APP_EXAMPLE_IDS})',
                'set_source_files_properties(${_cli}/'
                + full
                + '/project/analysis/analysis.edi PROPERTIES QT_RESOURCE_ALIAS wrong.edi)\n'
                + 'edi_app_bundle_examples(${_cli} ${EDI_APP_EXAMPLE_IDS})',
            ),
        ),
        ('prefix', cmake.replace('PREFIX "/edi/examples"', 'PREFIX "/wrong"')),
        (
            'target',
            cmake.replace('qt_add_resources(edi_app_module', 'qt_add_resources(unlinked_target'),
        ),
        (
            'metadata',
            cmake.replace(
                'list(APPEND bundled ${file})',
                'if(NOT file MATCHES "[.]edi$")\nlist(APPEND bundled ${file})\nendif()',
            ),
        ),
    ]:
        if dimension != label:
            continue
        bad, _ = resource_inventory(tmp_path / label, False, mutated)
        assert bundled_inputs(bad, full) != expected, (
            'Examples: each discarded identity dimension must reject its packaging escape'
        )
    if dimension in {'prefix', 'target', 'metadata', 'alias'}:
        return
    no_index = re.sub(r'qt_add_resources\(edi_app_module "edi_example_index"[\s\S]*?\)', '', cmake)
    if dimension == 'index':
        bad, index = resource_inventory(tmp_path / 'index', False, no_index)
        with pytest.raises(AssertionError, match='advertised index'):
            assert_bundled_index(bad, index)
        return
    injection = (
        '\nqt_add_resources(edi_app "other_label" PREFIX "/hidden" BASE '
        '${_cli} FILES ${_cli}/' + full + '/project/experiments/d20_scan/02_00601.dat)\n'
    )
    # Choose a frozen full-run file, independently of the bundle label.
    file = next(name for name in example_inventory(324) if name.startswith('02_'))
    injection = injection.replace('02_00601.dat', file)
    hidden, index = resource_inventory(
        tmp_path / 'hidden',
        True,
        cmake + injection,
    )
    with pytest.raises(AssertionError, match='web'):
        assert_web_exclusion(hidden, index)


def test_user_page_and_scale_adr_document_approved_limits():
    nav = (ROOT / 'mkdocs.yml').read_text()
    pages = [
        path
        for path in (ROOT / 'docs/user').rglob('*.md')
        if re.search(r'(?im)^#.*(?:sequential.*app|app.*sequential)', path.read_text())
    ]
    assert pages, 'Docs: a user page must explain sequential fitting in the app'
    assert any(path.name in nav for path in pages), (
        'Docs: the app scan guide must enter navigation'
    )
    adrs = [
        path.read_text()
        for path in (ROOT / 'docs/dev/adrs').glob('*.md')
        if re.search(r'1[ ,]?000[ ,]?000', path.read_text())
    ]
    assert adrs and any('scan' in text.lower() and 'results.csv' in text for text in adrs), (
        'Scale: the ADR must explain the million-file target and disk-backed result store'
    )


def cpp_probe(program, tmp_path):
    file = tmp_path / 'probe.cpp'
    file.write_text(program)
    executable = tmp_path / 'probe'
    built = subprocess.run(
        ['c++', '-std=c++20', str(file), '-o', str(executable)],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert built.returncode == 0, (
        'Scan wiring: the observed production operation must compile: ' + built.stderr
    )
    run = subprocess.run(
        [str(executable)], capture_output=True, text=True, check=False, timeout=10
    )
    assert run.returncode == 0, (
        'Scan wiring: the observed production operation must execute: ' + run.stderr
    )
    return run.stdout.splitlines()


def worker_dispatch(text, tmp_path):
    dispatch = block(text, 'FitResultBase fit_by_mode(')
    if 'FileCompleteCallback' not in dispatch:
        return ['REFUSED', 'REFUSED']
    program = """#include <iostream>
#include <string>
#include <stdexcept>
using IterationCallback=int; using PreambleCallback=int; using CancelCallback=int;

 using FileCompleteCallback=int;
using FitResultBase=std::string;
std::string receipt(std::string mode,std::initializer_list<int> args){

for(int arg:args)mode+=":"+std::to_string(arg);return mode;}
struct Project {std::string mode;
std::string fit(int a,int b,int c){return receipt("single",{a,b,c});

}
std::string fit_joint(int a,int b,int c){return receipt("joint",{a,
b,c});
}
std::string fit_sequential(int a,int b,int scan,int d,int c){
return receipt("sequential",{a,b,c,d});
}
std::string fit_independent(int a,int b,int scan,int d,int c){
return receipt("independent",{a,b,c,d});
}};
std::string effective_fitting_mode(Project& p){return p.mode;}
BODY
int main(){for(auto mode:{"sequential","independent"}){Project p{mode}

;try{std::cout<<fit_by_mode(p,11,22,33,44)<<"\\n";}catch(std::exception&
e){std::cout<<"REFUSED\\n";}}}""".replace('BODY', dispatch)
    return cpp_probe(program, tmp_path)


def joint_options(text, tmp_path):
    producer = block(text, 'void AnalysisViewModel::sync(')
    program = """#include <algorithm>
#include <iostream>
#include <string>
#include <vector>
#define emit
struct QString:std::string {using std::string::string;QString(std::string
x):std::string(x){}static QString fromStdString(std::string x){return QString(x);

}};
struct Scan{bool value=false;bool declared()const{return value;}};
struct Project{Scan sequential_fit;std::string descent;int minimizer_max_iterations=1;

double minimizer_chi_square_tolerance=0;};
namespace edi {std::string effective_fitting_mode(Project&){return "single";

}std::string default_descent(){return "lm";}int analysis_categories(Project&){

return 0;}std::vector<std::string> supported_fitting_modes(){return {

"single","joint","sequential","independent"};}}
struct Options{std::vector<std::string> tokens=edi::supported_fitting_modes();

void setOptions(std::vector<std::string> x,std::string ={}){tokens=x;

}void sync(){}void setCategories(int){}bool joint(){return std::find(tokens.begin(),

tokens.end(),"joint")!=tokens.end();}};
struct AnalysisViewModel {Project project_;QString fitting_mode_,descent_;

int max_iterations_=0;double chi_square_tolerance_=0;
Options options,other;Options* fitting_mode_options_=&options;Options*
joint_weights_=&other;Options* sequential_fit_=&other;Options* sequential_extract_=&other;

Options* fit_start_=&other;Options* aliases_=&other;Options* constraints_=&other;

Options* categories_=&other;
bool hasMaxIterations(){return max_iterations_!=0;}bool hasChiSquareTolerance(){

return chi_square_tolerance_!=0;}
void fittingModeChanged(){}void descentChanged(){}void maxIterationsChanged(){

}void hasMaxIterationsChanged(){}void chiSquareToleranceChanged(){}

void hasChiSquareToleranceChanged(){}
void sync();};
BODY
int main(){for(bool declared:{false,true,false}){AnalysisViewModel
model;model.project_.sequential_fit.value=declared;model.sync();std::cout<<model.options.joint()<<"\\n";

}}""".replace('BODY', producer)
    return cpp_probe(program, tmp_path)


def selection_follow(text, tmp_path):
    selection = block(text, 'void ProjectViewModel::setCurrentExperimentIndex(')
    program = """#include <iostream>
#include <vector>
struct Fit{bool following=true;void setFollowing(bool value){following=value;

}};
struct ProjectViewModel {int current_experiment_=1;std::vector<int>
experiment_models_{0,1,2};Fit model;Fit* fit_=&model;
void publishCurrent(){}void setCurrentExperimentIndex(int index);};


BODY
int main(){for(int index:{2,1,17}){ProjectViewModel model;model.setCurrentExperimentIndex(index);

std::cout<<model.model.following<<":"<<model.current_experiment_<<"\\n";

}}""".replace('BODY', selection)
    return cpp_probe(program, tmp_path)


def fit_state(header, model, tmp_path):
    declarations = []
    for name in ('continuable', 'scanning'):
        inline = re.search(r'bool ' + name + r'\(\) const\s*\{', header)
        declarations.append(
            block(header, 'bool ' + name + '() const')
            if inline
            else block(model, 'bool FitViewModel::' + name + '(').replace('FitViewModel::', '')
        )
    program = """#include <iostream>
struct Scan{bool value=false;bool declared()const{return value;}};struct
Project{Scan sequential_fit;};
struct FitViewModel {bool scanning_=false,continuable_=false,running_=false,

following_=false;Project project_;
BODY
};
int main(){for(int state:{0,1,2}){FitViewModel model;model.project_.sequential_fit.value=state>0;

model.running_=state==1;model.scanning_=state==1;model.continuable_=state==2;

std::cout<<model.scanning()<<":"<<model.continuable()<<"\\n";}}""".replace(
        'BODY', '\n'.join(declarations)
    )
    return cpp_probe(program, tmp_path)


def test_rendered_evolution_and_stale_observers_reject_unrelated_models_handlers_and_flags():
    good = """Item {
 Plot {
  model: view.results.points
  errors: model.uncertainty
  xValues: view.results.xValues
  onPointActivated: index => view.results.selectDataset(index)
 }
}"""
    assert_evolution_bindings(good)
    for old, new in [
        ('errors: model.uncertainty', 'errors: unrelated.uncertainty'),
        ('xValues: view.results.xValues', 'xValues: other.results.xValues'),
        (
            'onPointActivated: index => view.results.selectDataset(index)',
            'onPointActivated: index => view.results.selectDataset(0)',
        ),
        ('model: view.results.points', 'model: other.results.points'),
    ]:
        with pytest.raises((AssertionError, pytest.fail.Exception)):
            assert_evolution_bindings(good.replace(old, new))
    marker = """Item {
 Text {
  text: qsTr("out of date")
  visible: bar.fit.outOfDate
 }
}"""
    assert_stale_marker(marker)
    for changed in [
        marker.replace('visible: bar.fit.outOfDate', 'visible: other.fit.outOfDate'),
        marker.replace('visible: bar.fit.outOfDate', 'visible: true'),
        marker.replace('visible: bar.fit.outOfDate', 'visible: !bar.fit.outOfDate'),
        marker.replace('visible: bar.fit.outOfDate', 'visible: true')
        + '\nText { visible: bar.fit.outOfDate; text: "unrelated" }',
    ]:
        with pytest.raises((AssertionError, pytest.fail.Exception)):
            assert_stale_marker(changed)


def test_working_copy_observer_rejects_copy_to_an_unrelated_destination(monkeypatch):
    original = source
    current = original('src/session.cpp')
    changed = current.replace(
        'const QString destination = target + file.mid(source.size());',
        'const QString destination = source + file.mid(source.size());',
    )
    assert current != changed, (
        'Working-copy wiring: the escape must alter the effective copy destination'
    )
    monkeypatch.setattr(
        __import__(__name__, fromlist=['source']),
        'source',
        lambda path: changed if path == 'src/session.cpp' else original(path),
    )
    with pytest.raises(AssertionError):
        test_bundled_project_load_and_save_as_use_the_writable_copy_routes()


def test_resource_observer_accepts_a_separately_linked_example_library(tmp_path):
    cmake = (
        (APP / 'CMakeLists.txt')
        .read_text()
        .replace('if(EXISTS ${project}/analysis/analysis.edi)', 'if(FALSE)')
    )
    cmake = cmake.replace('qt_add_resources(edi_app_module', 'qt_add_resources(example_layer')
    cmake += '\ntarget_link_libraries(edi_app_module PRIVATE example_layer)\n'
    files, index = resource_inventory(tmp_path, False, cmake)
    assert_bundled_index(files, index)
    assert bundled_inputs(files, 'pd-neut-cwl_cosio-d20_scan-324f') == expected_bundle(324), (
        'Examples: resource inclusion follows the target linked to the app'
    )
