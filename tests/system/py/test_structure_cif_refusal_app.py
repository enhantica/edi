"""Load CIF admits supported structures and refuses ambiguous blocks atomically."""

import json
import os
import subprocess
from pathlib import Path

import edi
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
def test_load_cif_imports_supported_values_and_refuses_ambiguous_blocks(tmp_path, style):
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
    if style == 'multiblock':
        assert not outcome['accepted'] and '2 structure blocks' in outcome['error'], (
            'A singular Load CIF refuses ambiguous multiple structure blocks with their count'
        )
        assert outcome['afterCount'] == outcome['beforeCount'], (
            'An ambiguous structure import leaves the existing model intact'
        )
        assert case.saved_model(tmp_path / 'after') == case.saved_model(tmp_path / 'before'), (
            'Ambiguous CIF refusal preserves every saved model byte'
        )
    else:
        assert outcome['accepted'] and not outcome['error'], (
            'Load CIF accepts supported dot, underscore and uppercase declarations'
        )
        assert outcome['afterCount'] == outcome['beforeCount'] + 1, (
            'A supported CIF adds exactly its one declared structure'
        )
        loaded = edi.Project.load(tmp_path / 'after')
        checks.main_values(loaded.structures['cif_only'])
        after = case.saved_model(tmp_path / 'after')
        del after['structures/cif_only.edi']
        assert after == case.saved_model(tmp_path / 'before'), (
            'CIF admission preserves every pre-existing structure, experiment and analysis byte'
        )
    assert (tmp_path / 'input.cif').read_text() == case.text(style), (
        'The real application never rewrites the supplied CIF'
    )
