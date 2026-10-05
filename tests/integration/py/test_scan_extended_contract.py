"""Scan integration seams from the saved-file contract and owner records."""

from __future__ import annotations

import hashlib
import re
import shlex

import pytest
import yaml

from tests.integration.py.test_scan_app_contract import APP, ROOT, source


def test_scan_worker_routes_both_modes_to_existing_driver():
    text = (ROOT / 'core/src/fit_job.cpp').read_text()
    assert re.search(r'fit_sequential|sequential_fit', text), (
        'Scan run: the app worker must reach the existing scan driver'
    )
    assert re.search(r'file_complete|FileComplete|fileCompleted', text), (
        'Scan run: each committed driver row must reach the owner thread'
    )
    assert re.search(r'independent|is_scan_fitting_mode', text), (
        'Scan run: sequential and independent modes both use the scan driver'
    )


def test_scan_availability_and_joint_mode_follow_scan_declaration():
    fit = source('src/fit_view_model.cpp')
    assert 'single and joint fitting modes; this project' not in fit, (
        'Scan run: Start fitting must no longer refuse scan modes'
    )
    qml = source('qml/Pages/Analysis/FittingModeGroup.qml')
    models = source('src/analysis_view_model.cpp')
    assert re.search(r'scan|sequential_fit|data_dir', qml + models, re.IGNORECASE), (
        'Scan run: Joint mode must be disabled by the presence of a scan declaration'
    )


def test_scan_stop_continue_and_follow_have_model_state():
    header = source('src/fit_view_model.hpp')
    for concept in ('follow', 'continu', 'scan'):
        assert re.search(r'Q_PROPERTY\([^)]*' + concept, header, re.IGNORECASE), (
            'Scan interaction: continuation and following must be observable state'
        )
    cpp = source('src/project_view_model.cpp') + source('src/fit_view_model.cpp')
    assert re.search(r'[Ff]ollow[^;\n]*false|[Ff]ollow\(false\)', cpp), (
        'Follow: manual dataset selection must turn following off'
    )


def test_empty_selectors_are_hidden_on_experiment_and_structure_pages():
    for page in ('Experiment', 'Structure'):
        qml = source(f'qml/Pages/{page}/{page}Page.qml')
        workflow = source('qml/Components/WorkflowPage.qml')
        assert re.search(
            r'(?:visible|shown):[^\n]*(?:count\s*>\s*0|count\s*!==?\s*0|blocks[^\n]*count)',
            qml + workflow,
        ), 'Selectors: a page must hide its block selector when the project contains no blocks'


def test_selector_moves_to_main_tab_bar_once():
    qml = source('qml/Components/WorkflowPage.qml')
    assert qml.count('BlockSelector {') == 1, (
        'Selectors: the previous component must move rather than gain a duplicate'
    )
    assert re.search(
        r'mainTab[^\n]*|tabBar[^\n]*', qml[: qml.index('BlockSelector {')], re.IGNORECASE
    ), 'Selectors: the block selector must sit with the main-view tabs'
    assert not re.search(
        r'parent:\s*sideBar|anchors[^\n]*sideBar',
        qml[qml.index('BlockSelector {') : qml.index('BlockSelector {') + 1000],
    ), 'Selectors: the moved selector must not remain attached to the sidebar'


def test_scan_dataset_list_exposes_file_extracts_template_and_fit_roles():
    text = source('src/project_view_model.cpp')
    for concept in ('template', 'file', 'extract', 'fit'):
        assert re.search(concept, text, re.IGNORECASE), (
            'Datasets: rows expose the file, extracted values, template and outcome'
        )
    explorer = source('qml/Pages/Experiment/ExperimentsGroup.qml')
    assert 'Datablock' in explorer and 'File' in explorer, (
        'Datasets: explorer headers must distinguish the model datablock from the data file'
    )
    assert re.search(r'template', explorer, re.IGNORECASE), (
        'Datasets: the template dataset must carry its explicit text tag'
    )


def test_parameter_evolution_has_csv_model_errors_axis_switch_and_selection():
    files = list((APP / 'src').glob('*evolution*.*'))
    assert files, 'Evolution: results.csv must have a typed parameter-evolution view model'
    text = '\n'.join(path.read_text() for path in files)
    for concept in ('uncertainty', 'index', 'extract'):
        assert re.search(concept, text, re.IGNORECASE), (
            'Evolution: points must carry CSV uncertainties, file index and extracted coordinates'
        )
    qml_files = list((APP / 'qml').rglob('*Evolution*.qml'))
    assert qml_files, 'Evolution: the main view must expose the second parameter-evolution tab'
    qml = '\n'.join(path.read_text() for path in qml_files)
    assert re.search(r'on(?:Clicked|Point|Activated)', qml) and re.search(
        r'select|current.*Index', qml, re.IGNORECASE
    ), 'Evolution: clicking a point selects its dataset everywhere'


def test_old_scan_results_are_retained_with_out_of_date_state():
    text = '\n'.join(path.read_text() for path in (APP / 'src').glob('*.hpp'))
    assert re.search(r'Q_PROPERTY\([^)]*(?:[Oo]ut[Oo]f[Dd]ate|[Ss]tale)', text), (
        'Out of date: old scan results need observable state after a template edit'
    )
    qml = '\n'.join(path.read_text() for path in (APP / 'qml').rglob('*.qml'))
    assert 'out of date' in qml.lower(), (
        'Out of date: the retained results summary and evolution tab must show stale state'
    )


def test_read_only_scan_has_a_writable_project_copy():
    cpp = source('src/project_view_model.cpp') + source('src/session.cpp')
    assert re.search(r'QTemporaryDir|temporary_directory|temp_directory_path', cpp), (
        'Read-only scan: bundled projects must fit in a temporary working copy'
    )
    assert 'results.csv' in cpp, 'Read-only scan: Save As must retain the scan result store'


@pytest.mark.parametrize('count', [162, 324])
def test_scan_examples_have_exact_source_file_inventory_and_checksums(count):
    project_id = f'pd-neut-cwl_cosio-d20_scan-{count}f'
    base = ROOT / 'docs/user/cli' / project_id
    assert base.is_dir(), 'Examples: both declared scan projects must exist in the CLI plane'
    declaration = (base / 'project/analysis/analysis.edi').read_text()
    data_dir = next(
        shlex.split(line)[1]
        for line in declaration.splitlines()
        if line.startswith('_sequential_fit.data_dir ')
    )
    files = sorted((base / 'project' / data_dir).glob('*.dat'))
    assert len(files) == count, 'Examples: scan input count must equal the owner-selected run'
    provenance = (base / 'PROVENANCE.md').read_text()
    for file in files:
        assert (
            file.name in provenance and hashlib.sha256(file.read_bytes()).hexdigest() in provenance
        ), 'Examples: provenance names every bundled source file by checksum'
    if count == 162:
        assert all(file.name.startswith('01_') for file in files), (
            'Examples: the smaller scan contains only the cooling run'
        )
    registry = yaml.safe_load((ROOT / 'docs/user/cli/projects.yml').read_text())['projects']
    assert any(row['id'] == project_id for row in registry), (
        'Examples: the CLI registry must expose both scans'
    )
    cmake = (APP / 'CMakeLists.txt').read_text()
    assert project_id in cmake, 'Examples: the desktop bundle must include both declared scans'


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
