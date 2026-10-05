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
    item,
    property_value,
    require,
    source,
)


def test_scan_worker_routes_both_modes_to_existing_driver():
    text = re.sub(
        r'//[^\n]*|/\*.*?\*/', '', (ROOT / 'core/src/fit_job.cpp').read_text(), flags=re.DOTALL
    )
    dispatch = block(text, 'FitResultBase fit_by_mode(')
    for mode in ('sequential', 'independent'):
        require(
            dispatch,
            r'return project\.fit_' + mode + r'\([^;]*file_complete',
            'Scan worker wiring: each mode calls the driver with its completion subscriber',
        )


def test_scan_availability_and_joint_mode_follow_scan_declaration():
    model = source('src/analysis_view_model.cpp')
    # Observe the option producer consumed by the actual mode selector.
    require(
        source('qml/Pages/Analysis/FittingModeGroup.qml'),
        r'options:\s*row\.analysis\s*\?\s*row\.analysis\.fittingModeOptions',
        'Scan mode wiring: the actual picker uses the guarded options model',
    )
    producer = block(model, 'void AnalysisViewModel::sync(')
    require(
        producer,
        r'fitting_mode_options_->[^;]*\b(?:scan|sequential_fit)',
        'Scan mode wiring: the consumed options producer must disable joint for scan projects',
    )


def test_scan_stop_continue_and_follow_have_model_state():
    text = source('src/project_view_model.cpp')
    selection = block(text, 'void ProjectViewModel::setCurrentExperimentIndex(')
    require(
        selection,
        r'(?:setFollowing|set_following)\(false\)',
        'Follow wiring: manual selection must turn following off in its actual selection handler',
    )
    header = source('src/fit_view_model.hpp')
    for name in ('continuable', 'scanning'):
        assert not re.search(r'bool ' + name + r'\(\) const \{ return false; \}', header), (
            'Scan state wiring: consumed state cannot be a permanent false placeholder'
        )


def test_empty_selectors_are_hidden_on_experiment_and_structure_pages():
    workflow = source('qml/Components/WorkflowPage.qml')
    selector = block(workflow, 'MainAreaBlockSelector {')
    assert (
        property_value(selector, 'visible')
        == 'page.blockSelectorShown && page.blocks !== null && page.blocks.count > 0'
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


def test_scan_explorer_header_has_declared_columns_in_order():
    header = block(source('qml/Pages/Experiment/ExperimentsGroup.qml'), 'header:')
    labels = re.findall(r'text:\s*qsTr\("([^\"]+)"\)', header)
    assert labels[:4] == ['No.', 'Fit', 'Datablock', 'File'], (
        'Dataset list labels: scan columns appear in number, fit, datablock, file order'
    )
    require(
        header,
        r'Repeater\s*\{[^}]*model:\s*[^\n]+\.',
        'Dataset list wiring: dynamic extract columns use their actual column model',
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


def test_parameter_evolution_has_csv_model_errors_axis_switch_and_selection():
    qml = evolution_component()
    require(
        qml,
        r'(?:error|uncertainty)[^\n]*:\s*[^\n]*(?:model|series|points)\.',
        'Evolution wiring: error bars bind to the actual point model',
    )
    require(
        qml,
        r'on(?:Clicked|PointActivated):[^}]*\.(?:selectDataset|setCurrentExperimentIndex)\(',
        'Evolution wiring: the actual point handler routes dataset selection',
    )
    require(
        qml,
        r'(?:xValues|xAxis|axisMode):[^\n]*\.',
        'Evolution wiring: the displayed x coordinates read switchable model state',
    )


def test_old_scan_results_are_retained_with_out_of_date_state():
    bar = item(source('qml/Components/StatusBar.qml'), 'statusBar.fit')
    evolution = evolution_component()
    for consumer in (bar, evolution):
        require(
            consumer,
            r'(?:text|segments):[^}]*out of date',
            'Stale-result wiring: each actual results consumer displays the marker',
        )
        require(
            consumer,
            r'(?:visible|text|segments):[^}]*\.(?:outOfDate|stale)',
            'Stale-result wiring: each marker reads the consumed model state',
        )


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
    start = cmake.index('set(_cli ')
    end = cmake.index('# The licences', start)
    body = cmake[start:end]
    scratch = tmp_path / ('web' if web else 'desktop')
    scratch.mkdir(parents=True)
    receipt = scratch / 'inventory.tsv'
    harness = f"""cmake_minimum_required(VERSION 3.25)
project(ResourceProbe NONE)
set(PROJECT_SOURCE_DIR "{ROOT.as_posix()}")
set(CMAKE_CURRENT_SOURCE_DIR "{APP.as_posix()}")
set(EMSCRIPTEN {'TRUE' if web else 'FALSE'})
file(WRITE "{receipt.as_posix()}" "")
function(qt_add_resources target resource)
 cmake_parse_arguments(ARG "" "PREFIX;BASE" "FILES;OPTIONS" ${{ARGN}})
 foreach(file IN LISTS ARG_FILES)
  file(RELATIVE_PATH relative "${{ARG_BASE}}" "${{file}}")
  file(SHA256 "${{file}}" digest)
  file(APPEND "{receipt.as_posix()}" "${{resource}}\\t${{relative}}\\t${{digest}}\\n")
 endforeach()
endfunction()
{body}
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
    return receipt.read_text().splitlines(), (
        scratch / 'build/examples/index.txt'
    ).read_text().splitlines()


def bundled_inputs(files, project_id):
    records = [
        line.split('\t') for line in files if line.startswith('edi_example_' + project_id + '\t')
    ]
    return {
        relative: digest for _resource, relative, digest in records if relative.endswith('.dat')
    }


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
    return {
        f'{project_id}/project/{declaration["_sequential_fit.data_dir"]}/{name}': digest
        for name, digest in inventory.items()
    }


@pytest.mark.parametrize('web', [False, True], ids=['desktop', 'web'])
def test_effective_bundle_contains_selected_scan_payloads(tmp_path, web):
    files, index = resource_inventory(tmp_path, web)
    small = 'pd-neut-cwl_cosio-d20_scan-162f'
    large = 'pd-neut-cwl_cosio-d20_scan-324f'
    assert small in index, 'Examples: the cooling run must be offered in desktop and web'
    assert bundled_inputs(files, small) == expected_bundle(162), (
        'Examples: cooling resources bind every input path to its frozen source bytes'
    )
    if web:
        assert large not in index and not bundled_inputs(files, large), (
            'Examples: the full scan is absent from the web index and resource payload'
        )
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
