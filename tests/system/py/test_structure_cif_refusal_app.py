"""Load CIF refuses atomically in the production Qt session."""

import json
import os
import subprocess
from pathlib import Path

import pytest

from tests.fixtures import structure_cif_refusal as case
from tests.integration.py import structure_cif_refusal_checks as checks

ROOT = Path(__file__).resolve().parents[3]
QML = """import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
TestCase {
    name: "StructureCifRefusal"
    when: true
    function test_refusal() {
        Session.openProject(Probe.referenceUrl("project"));
        verify(Session.hasProject, "The native control opens before the real Load CIF action");
        const beforeCount = Probe.rows(Session.project.structures).length;
        verify(Session.saveAs(Probe.referenceUrl("before")),
               "The complete native model reaches its before-import save boundary");
        const beforeWarnings = Probe.rows(Session.loadWarnings).length;
        const accepted = Session.project.loadStructure(Probe.referenceUrl("input.cif"));
        const error = Session.project.lastError || Session.lastError;
        const messages = Probe.rows(Session.loadWarnings).slice(beforeWarnings)
                             .map(row => row.message);
        const afterCount = Probe.rows(Session.project.structures).length;
        verify(Session.saveAs(Probe.referenceUrl("after")),
               "The complete model remains saveable after the attempted structure import");
        verify(Probe.appendNotes(Probe.referenceUrl("outcome.json"), JSON.stringify({
                   accepted, error, messages, beforeCount, afterCount})),
               "The real Load CIF outcome is recorded for independent readback");
        Session.closeProject();
    }
}
"""


@pytest.mark.parametrize('style', ['dot', 'underscore', 'upper', 'multiblock'])
def test_load_cif_refuses_with_one_reason_and_keeps_the_model(tmp_path, style):
    case.project(tmp_path)
    (tmp_path / 'input.cif').write_text(case.text(style))
    (tmp_path / 'outcome.json').touch()
    script = tmp_path / 'tst_structure_refusal.qml'
    script.write_text(QML)
    binary = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert binary.is_file(), 'The refusal gate uses the real application test host'
    result = subprocess.run(
        [str(binary), '-input', str(script), '-o', '-,txt'],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
        env={
            **os.environ,
            'EDI_ACCEPTANCE_REFERENCE': str(tmp_path),
            'QT_QPA_PLATFORM': 'offscreen',
            'QT_QUICK_BACKEND': 'software',
            'OMP_NUM_THREADS': '1',
        },
    )
    assert result.returncode == 0, (
        'The actual Load CIF actor reaches both save boundaries: ' + result.stdout + result.stderr
    )
    outcome = json.loads((tmp_path / 'outcome.json').read_text())
    assert not outcome['accepted'], 'Load CIF refuses the deferred structure import'
    checks.reason(outcome['error'])
    assert all(note == outcome['error'] for note in outcome['messages']), (
        'The refused import has one reason rather than partial-import warnings'
    )
    assert outcome['afterCount'] == outcome['beforeCount'], (
        'Load CIF refusal adds and removes no structure in the existing project'
    )
    assert case.saved_model(tmp_path / 'after') == case.saved_model(tmp_path / 'before'), (
        'Every saved structure, experiment and analysis byte survives the refused Load CIF action'
    )
