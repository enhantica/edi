"""Copied browser datasets remain usable before and after the first project save."""

import os
import shutil
import subprocess
from pathlib import Path

import pytest

from tests.fixtures.structure_cif_refusal import CIF

ROOT = Path(__file__).resolve().parents[3]
PREPARE = """import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
TestCase {
    name: "BrowserDatasetCopy"
    when: true
    function test_copy() {
        verify(Session.createProject("browser_copy", ""), "Create the actual unsaved project");
        const project = Session.project;
        verify(project.loadStructure(Probe.referenceUrl("structure.cif")),
               "Load the authored structure");
        verify(project.createExperiment(), "Create the real measured-data target");
        verify(project.loadDataInto(project.currentExperiment, Probe.referenceUrl("upload/a.xye")),
               "Load the initial measured template");
        if (SAVED)
            verify(Session.saveAs(Probe.referenceUrl("initial")),
                   "Save the ordinary project first");
        const beforePath = project.path;
        const beforeMetadata = project.metadataText.text;
        project.loadDatasetFolder(project.currentExperiment, Probe.referenceUrl("upload"), true);
        tryCompare(project, "listingDatasetFolder", false, 5000);
        verify(project.scan, "Copied folder becomes a real scan: " + project.lastError);
        compare(project.path, beforePath, "Copying datasets does not assign a project location");
        compare(project.metadataText.text, beforeMetadata,
               "Dataset copying preserves project metadata");
        if (!SAVED)
            compare(project.path, "", "The uploaded scan remains unsaved before Save as");
        verify(Session.saveAs(Probe.referenceUrl("saved")),
               "First Save copies the held scan data");
        Session.closeProject();
    }
}
"""
RELOAD = """import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
TestCase {
    name: "BrowserDatasetReload"
    when: true
    function test_reload() {
        verify(Session.openProject(Probe.referenceUrl("saved")), "Reopen the copied scan project");
        const project = Session.project;
        verify(project.scan, "The saved scan retains its dataset declaration");
        compare(project.missingDataFolder, "", "No uploaded folder is needed after saving");
        project.scanViews.wanted = true;
        tryCompare(project.scanViews, "loaded", 2, 5000);
        compare(project.scanViews.failed, 0,
               "Both actual copied datasets are independently readable");
        verify(Session.saveAs(Probe.referenceUrl("resaved")),
               "A reopened copied scan remains portable");
        Session.closeProject();
    }
}
"""
GEOMETRY = """import QtQuick
import QtTest
import edi.app
TestCase {
    name: "LoadMenuColumns"
    when: windowShown
    function test_columns() {
        const component = Qt.createComponent(SOURCE);
        compare(component.status, Component.Ready,
               "Load the actual menu component: " + component.errorString());
        const rows = [];
        for (const text of ["From file…", "From folder…", "A longer source action"])
            rows.push(component.createObject(this,
                {text:text, hint:"A long dataset-format hint", width:340}));
        for (const row of rows)
            verify(row !== null, "Each actual Load menu row is created");
        wait(0);
        const origin = rows[0].contentItem.children[2].x;
        for (const row of rows) {
            compare(row.contentItem.children[2].x, origin,
                   "Hints align independently of action text length");
            compare(row.contentItem.children[1].elide, Text.ElideRight,
                   "Long actions preserve the fixed column");
            row.width = 180;
        }
        wait(0);
        for (const row of rows) {
            const hint = row.contentItem.children[2];
            verify(hint.width >= 0, "A narrow menu never assigns negative hint geometry");
            compare(hint.elide, Text.ElideRight,
                   "Narrow hints elide instead of shifting another column");
            verify(hint.truncated || hint.width === 0,
                   "The long hint is actually bounded in the narrow menu");
            row.destroy();
        }
    }
}
"""


def actor(root, script, name):
    binary = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert binary.is_file(), 'Browser dataset persistence uses the actual native application actor'
    path = root / ('tst_' + name + '.qml')
    path.write_text(script, encoding='utf-8')
    result = subprocess.run(
        [str(binary), '-input', str(path), '-o', '-,txt'],
        env={
            **os.environ,
            'EDI_ACCEPTANCE_REFERENCE': str(root),
            'QT_QPA_PLATFORM': 'offscreen',
            'QT_QUICK_BACKEND': 'software',
            'OMP_NUM_THREADS': '1',
        },
        capture_output=True,
        text=True,
        check=False,
        timeout=20,
    )
    (root / (name + '.log')).write_text(result.stdout + result.stderr, encoding='utf-8')
    assert result.returncode == 0, (
        'The actual application actor reaches its dataset or geometry contract: '
        + result.stdout
        + result.stderr
    )


@pytest.mark.parametrize('saved', [False, True], ids=['unsaved', 'saved'])
def test_copied_folder_survives_save_upload_removal_and_reload(tmp_path, saved):
    upload = tmp_path / 'upload'
    upload.mkdir()
    (tmp_path / 'structure.cif').write_text(CIF, encoding='utf-8')
    originals = {
        name: ''.join(f'{10 + index} {20 + number + index} 1\n' for index in range(7)).encode()
        for number, name in enumerate(['a.xye', 'b.xye'])
    }
    for name, data in originals.items():
        (upload / name).write_bytes(data)
    actor(tmp_path, PREPARE.replace('SAVED', str(saved).lower()), 'copy')
    for name, data in originals.items():
        assert (upload / name).read_bytes() == data, (
            'Copying never rewrites the uploaded dataset input'
        )
        copied = list((tmp_path / 'saved/scans').rglob(name))
        assert len(copied) == 1, 'The saved scan owns exactly one copy of each selected dataset'
        assert copied[0].read_bytes() == data, (
            'Each saved scan dataset retains its exact uploaded bytes'
        )
    shutil.rmtree(upload)
    actor(tmp_path, RELOAD, 'reload')
    for name, data in originals.items():
        copied = list((tmp_path / 'resaved/scans').rglob(name))
        assert len(copied) == 1, (
            'The second project save retains every originally selected dataset'
        )
        assert copied[0].read_bytes() == data, (
            'Reopening and resaving preserves independent dataset bytes'
        )


def test_load_menu_hints_share_a_column_and_remain_bounded(tmp_path):
    import json  # noqa: PLC0415 - portable QML source URL

    source = (ROOT / 'app/qml/Components/LoadMenuItem.qml').as_uri()
    actor(tmp_path, GEOMETRY.replace('SOURCE', json.dumps(source)), 'geometry')
