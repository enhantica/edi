"""The production native experiment loader refuses both orders of a mixed batch."""

import json
import os
import subprocess
from pathlib import Path

import pytest

from tests.fixtures import experiment_cif_refusal as case
from tests.fixtures import structure_cif_refusal as native
from tests.integration.py import experiment_cif_refusal_checks as checks

ROOT = Path(__file__).resolve().parents[3]
QML = """import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
TestCase {
    name: "ExperimentCifRefusal"
    when: true
    function test_refusal() {
        Session.openProject(Probe.referenceUrl("project"));
        verify(Session.hasProject, "The native project opens before experiment loading");
        verify(Session.project.loadExperiments([Probe.referenceUrl("extra.edi")]),
               "The production native loader accepts a native experiment control");
        verify(Session.saveAs(Probe.referenceUrl("control")),
               "The native experiment control reaches the complete save boundary");
        Session.closeProject();
        Session.openProject(Probe.referenceUrl("project"));
        verify(Session.hasProject, "The original native project is reopened for batch refusal");
        const beforeCount = Probe.rows(Session.project.experiments).length;
        verify(Session.saveAs(Probe.referenceUrl("before")),
               "Every native model byte reaches its before-import save boundary");
        const beforeWarnings = Probe.rows(Session.loadWarnings).length;
        const names = JSON.parse(Probe.readReferenceFile("batch.json"));
        const paths = names.map(name => Probe.referenceUrl(name));
        const accepted = Session.project.loadExperiments(paths);
        const error = Session.project.lastError || Session.lastError;
        const messages = Probe.rows(Session.loadWarnings).slice(beforeWarnings)
                             .map(row => row.message);
        const afterCount = Probe.rows(Session.project.experiments).length;
        verify(Session.saveAs(Probe.referenceUrl("after")),
               "The whole project remains saveable after the refused batch");
        verify(Probe.appendNotes(Probe.referenceUrl("outcome.json"), JSON.stringify({
                   accepted, error, messages, beforeCount, afterCount})),
               "The production loader records its actual terminal outcome");
        Session.closeProject();
    }
}
"""


@pytest.mark.parametrize('style', case.STYLES)
@pytest.mark.parametrize('order', ['cif-first', 'native-first'])
def test_native_experiment_loader_refuses_a_cif_batch_atomically(tmp_path, style, order):
    native.project(tmp_path)
    case.native_experiment(tmp_path)
    (tmp_path / 'input.edi').write_text(case.text(style))
    paths = ['input.edi', 'extra.edi'] if order == 'cif-first' else ['extra.edi', 'input.edi']
    (tmp_path / 'batch.json').write_text(json.dumps(paths))
    (tmp_path / 'outcome.json').touch()
    script = tmp_path / 'tst_experiment_refusal.qml'
    script.write_text(QML)
    binary = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
    assert binary.is_file(), 'Experiment refusal uses the real application test host'
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
        'The actual experiment loader reaches every native control and save boundary: '
        + result.stdout
        + result.stderr
    )
    outcome = json.loads((tmp_path / 'outcome.json').read_text())
    assert not outcome['accepted'], (
        'The application refuses a CIF even when it has a native suffix'
    )
    checks.reason(outcome['error'])
    assert not outcome['messages'], 'A refused batch has no partial-import warnings'
    assert outcome['afterCount'] == outcome['beforeCount'], (
        'Neither ordering of a refused mixed batch adds or removes an experiment'
    )
    assert native.saved_model(tmp_path / 'after') == native.saved_model(tmp_path / 'before'), (
        'A mixed experiment batch preserves every saved native model byte on refusal'
    )
    assert (tmp_path / 'input.edi').read_text() == case.text(style), (
        'The app never normalizes or rewrites a refused CIF input'
    )
    assert (tmp_path / 'control/experiments/extra.edi').is_file(), (
        'The same production native loader imports and saves its native experiment control'
    )
