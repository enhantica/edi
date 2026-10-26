"""Real CLI and app entrances retain or report every authored CIF declaration."""

import json
import os
import shutil
import subprocess
import sys
from operator import itemgetter
from pathlib import Path

import pytest

from tests.fixtures import cif_import_cases as case

ROOT = Path(__file__).resolve().parents[3]
QML = """import QtQuick
import QtTest
import edi.app
import EdiAcceptance 1.0
TestCase {
    name: "CifConsumption"
    when: true
    function test_declaration_data() {
        return JSON.parse(Probe.readReferenceFile("manifest.json"));
    }
    function test_declaration(data) {
        Session.openProject(Probe.referenceUrl("base"));
        verify(Session.hasProject, "Load CIF begins with the valid independent project");
        const before = Probe.rows(Session.loadWarnings).length;
        const accepted = data.kind === "structure"
            ? Session.project.loadStructure(Probe.referenceUrl(data.input))
            : Session.project.loadExperiments([Probe.referenceUrl(data.input)]);
        const messages = Probe.rows(Session.loadWarnings).map(row => row.message);
        if (data.tag === "control")
            verify(accepted, "The Load CIF control must import its valid authored structure");
        if (accepted)
            verify(Session.saveAs(Probe.referenceUrl(data.output)),
                   "Accepted CIF declarations reach the real application save boundary");
        else
            verify(messages.length > before || Session.project.lastError.length > 0,
                   "A refused Load CIF supplies its diagnostic");
        verify(Probe.appendNotes(Probe.referenceUrl("outcomes.jsonl"),
                                 JSON.stringify({tag: data.tag, accepted, messages,
                                                 refused: Session.project.lastError}) + "\\n"),
               "Every attempted app declaration has one observed result");
        Session.closeProject();
    }
}
"""
CLI = r"""import contextlib, io, json, os, sys, tempfile, types, warnings
from pathlib import Path
import edi
import edi.__main__ as cli
root = Path(sys.argv[1])
load = edi.Project.load
current = None
class ObservedProject:
    @staticmethod
    def load(path):
        project = load(path)
        project.save_as(root / current['output'])
        return project
cli.edi = types.SimpleNamespace(**vars(edi))
cli.edi.Project = ObservedProject
for entry in json.loads((root / 'manifest.json').read_text()):
    current = entry
    out, err = io.StringIO(), io.StringIO()
    refusal = ''
    with tempfile.TemporaryFile(mode='w+') as native:
        original_fd = os.dup(2)
        os.dup2(native.fileno(), 2)
        try:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter('always')
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    try:
                        code = cli.main(['report', str(root / entry['input']), '--check'])
                    except (ValueError, RuntimeError) as error:
                        refusal = str(error)
        finally:
            os.dup2(original_fd, 2)
            os.close(original_fd)
        native.seek(0)
        native_lines = native.read().splitlines()
    folder = 'structures' if entry['kind'] == 'structure' else 'experiments'
    accepted = (root / entry['output'] / folder / 'witness.edi').is_file()
    messages = [str(w.message) for w in caught] + err.getvalue().splitlines() + native_lines
    with (root / 'outcomes.jsonl').open('a') as target:
        target.write(json.dumps(dict(tag=entry['tag'], accepted=accepted,
                                    messages=messages, refused=refusal or err.getvalue())) + '\n')
"""


def observe(tmp_path, route, kind, payloads, *, native=False):
    manifest = []
    for i, text in enumerate(payloads):
        folder = tmp_path / str(i)
        folder.mkdir()
        if route == 'cli':
            source = case.project_input(kind, text, folder, '.edi' if native else '.cif')
        else:
            source = folder / ('input.edi' if native else 'input.cif')
            source.write_text(text)
        manifest.append({
            'tag': 'control' if i == 0 else str(i),
            'kind': kind,
            'input': str(source.relative_to(tmp_path)),
            'output': str(i) + '-saved',
        })
    (tmp_path / 'manifest.json').write_text(json.dumps(manifest))
    (tmp_path / 'outcomes.jsonl').touch()
    environment = {**os.environ, 'OMP_NUM_THREADS': '1'}
    if route == 'cli':
        actor = tmp_path / 'observe_cli.py'
        actor.write_text(CLI)
        command = [sys.executable, str(actor), str(tmp_path)]
    else:
        shutil.copytree(ROOT / 'tests/fixtures/loop_parameter_ids/line-segment', tmp_path / 'base')
        actor = tmp_path / 'tst_import.qml'
        actor.write_text(QML)
        binary = Path(os.environ.get('EDI_APP_TEST_RUNNER', ROOT / 'build/app/app/edi_app_tests'))
        assert binary.is_file(), 'Public app gates require the built production Qt test host'
        command = [str(binary), '-input', str(actor), '-o', '-,txt']
        environment.update(
            EDI_ACCEPTANCE_REFERENCE=str(tmp_path),
            QT_QPA_PLATFORM='offscreen',
            QT_QUICK_BACKEND='software',
        )
    process = subprocess.run(
        command, env=environment, capture_output=True, text=True, check=False, timeout=20
    )
    assert process.returncode == 0, (
        'The real public actor reaches every payload: ' + process.stdout + process.stderr
    )
    outcomes = [
        json.loads(line) for line in (tmp_path / 'outcomes.jsonl').read_text().splitlines()
    ]
    assert len(outcomes) == len(payloads), (
        'Every public entrance attempt produces exactly one observable result'
    )
    results = []
    for i, outcome in enumerate(outcomes):
        if not outcome['accepted']:
            results.append({
                'refused': outcome['refused'] or ' '.join(outcome['messages']),
                'notes': outcome['messages'],
            })
        else:
            folder = 'structures' if kind == 'structure' else 'experiments'
            target = tmp_path / (str(i) + '-saved') / folder / 'witness.edi'
            results.append({
                'cells': case.columns(target.read_text()),
                'notes': outcome['messages'],
            })
    assert 'refused' not in results[0], (
        'The public entrance first imports its valid nondefault CIF control'
    )
    return results[1:]


@pytest.mark.parametrize('route', ['cli', 'app'])
@pytest.mark.parametrize('kind', ['structure', 'experiment'])
@pytest.mark.parametrize('row', case.inventory(), ids=itemgetter('uid'))
def test_public_entrances_account_for_every_alias_and_loop_cell(tmp_path, route, kind, row):
    declarations = []
    inputs = [case.STRUCTURE if kind == 'structure' else case.EXPERIMENT]
    for name in row['cif_names']:
        for spelling in dict.fromkeys([name, name.replace('.', '_', 1).upper()]):
            for shape in ['item', 'column']:
                for value in [case.token(row), '?', '.', "'?'", "''"]:
                    inputs.append(case.payload(kind, row, spelling, shape, value))
                    declarations.append((spelling, value, shape))
    results = observe(tmp_path, route, kind, inputs)
    for result, (name, value, shape) in zip(results, declarations, strict=True):
        case.accounted(
            result, name, value, row['edi_names'][0], count=2 if shape == 'column' else 1
        )


@pytest.mark.parametrize('route', ['cli', 'app'])
@pytest.mark.parametrize('kind', ['structure', 'experiment'])
def test_public_entrances_keep_cif_grammar_and_parser_refusals(tmp_path, route, kind):
    control = case.STRUCTURE if kind == 'structure' else case.EXPERIMENT
    wrapped = control.replace('_cell_length_a 5.1000', '_cell_length_a\n5.1000').replace(
        '10 21 2', '10\n21 2'
    )
    results = observe(
        tmp_path, route, kind, [control, wrapped, control + "_audit.note 'unterminated\n"]
    )
    assert 'refused' not in results[0], 'The real public entrance accepts wrapped CIF tokens'
    assert 'refused' in results[1], (
        'The public entrance must refuse malformed CIF instead of retrying another reader'
    )
    assert results[1]['refused'], 'The public parser refusal retains its reason'


@pytest.mark.parametrize('route', ['cli', 'app'])
@pytest.mark.parametrize('kind', ['structure', 'experiment'])
def test_public_observer_reaches_the_existing_native_reader(tmp_path, route, kind):
    folder = 'structures' if kind == 'structure' else 'experiments'
    name = 'phase.edi' if kind == 'structure' else 'bank.edi'
    text = (ROOT / 'tests/fixtures/loop_parameter_ids/line-segment' / folder / name).read_text()
    text = text.replace('data_phase', 'data_witness', 1).replace('data_bank', 'data_witness', 1)
    results = observe(tmp_path, route, kind, [text, text], native=True)
    assert 'refused' not in results[0], (
        'The public observer has a working native import and saved-model control'
    )
