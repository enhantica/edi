"""Real CLI and app entrances retain or report every authored CIF declaration."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import edi
import gemmi
import pytest

from tests.fixtures import cif_import_cases as case
from tests.fixtures.project_save.reference import six_digits

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
                'saved': target.parents[1],
                'notes': outcome['messages'],
            })
    assert 'refused' not in results[0], (
        'The public entrance first imports its valid nondefault CIF control'
    )
    return results[1:]


@pytest.fixture(scope='module')
def public_app_runtime(tmp_path_factory):
    # The first actual Qt import/save warms the runtime once, outside any measured call.
    # Use the same valid-control observer so setup failures remain visible failures.
    observe(tmp_path_factory.mktemp('cif-public-app-warmup'), 'app', 'structure', [case.STRUCTURE])


@pytest.fixture(autouse=True)
def prepare_public_entrance(route, request):
    if route == 'app':
        request.getfixturevalue('public_app_runtime')


@pytest.mark.parametrize('route', ['cli', 'app'])
@pytest.mark.parametrize('kind', ['structure', 'experiment'])
@pytest.mark.parametrize('layout', ['item', 'column'])
@pytest.mark.parametrize(
    'probe',
    [
        (row, spelling, witness)
        for row in case.inventory()
        for name in row['cif_names']
        for spelling in dict.fromkeys([name, name.replace('.', '_', 1).upper()])
        for witness in range(5)
    ],
    ids=[
        row['uid'] + ':' + name + ':s' + str(style) + ':v' + str(witness)
        for row in case.inventory()
        for name in row['cif_names']
        for style, _ in enumerate(dict.fromkeys([name, name.replace('.', '_', 1).upper()]))
        for witness in range(5)
    ],
)
def test_public_entrances_account_for_every_alias_and_loop_cell(
    tmp_path, route, kind, probe, layout
):
    row, spelling, witness = probe
    declarations = []
    inputs = [case.STRUCTURE if kind == 'structure' else case.EXPERIMENT]
    keys = (
        ('Ba', 'O')
        if kind == 'structure'
        and layout == 'column'
        and row['uid'].startswith('atom_type_scat.neutron_magnetic_')
        else ()
    )
    numeric_coefficient = bool(keys) and row['uid'].startswith('atom_type_scat.neutron_magnetic_j')
    good = '0.271828' if numeric_coefficient else case.token(row)
    values = [good, '?', '.', "'?'", "''"]
    for value in [values[witness]]:
        inputs.append(case.payload(kind, row, spelling, layout, value, atom_type_keys=keys))
        declarations.append((spelling, value, layout))
    results = observe(tmp_path, route, kind, inputs)
    for result, (name, value, shape) in zip(results, declarations, strict=True):
        if keys:
            assert_scattering_rows(
                result, name, value, row['edi_names'][0], keys, numeric_coefficient
            )
        if keys and row['uid'] == 'atom_type_scat.neutron_magnetic_source' and value == "''":
            assert_quoted_empty_sources_on_two_saves(result['saved'], keys, (value, value))
        case.accounted(
            result,
            name,
            (
                str(six_digits(float(value)))
                if row.get('dtype') in {'float', 'number'} and value == case.token(row)
                else value
            ),
            row['edi_names'][0],
            count=2 if shape == 'column' else 1,
        )


def assert_scattering_rows(result, name, value, canonical, keys, numeric_coefficient):
    if numeric_coefficient and value.startswith("'"):
        refusal = result.get('refused', '')
        assert case.notices(refusal, name) and value in refusal, (
            'A supplied quoted coefficient marker refuses at its own tag and value'
        )
        assert 'not a finite number' in refusal, (
            'The keyed coefficient loop reaches numeric validation'
        )
        return
    assert 'refused' not in result, (
        'The two valid atom-type keys admit the supplied or absent coefficient: '
        + result.get('refused', '')
    )
    cells = result['cells']
    stored_keys = cells.get(case.key('_atom_type_scat.symbol'), [])
    assert [case.decoded(symbol) for symbol in stored_keys] == list(keys), (
        'The two scattering rows retain their distinct atom-type keys in order'
    )
    if value in {'?', '.'}:
        assert case.key(canonical) not in cells, (
            'Two bare missing markers leave no supplied coefficient column'
        )


def assert_quoted_empty_sources_on_two_saves(first, keys, tokens):
    expected = list(zip(keys, tokens, strict=True))
    second = first.with_name(first.name + '-again')
    for saved in (first, second):
        text = (saved / 'structures/witness.edi').read_text()
        if not text.lstrip().lower().startswith('data_'):
            text = 'data_saved\n' + text
        block = gemmi.cif.read_string(text).sole_block()
        table = block.find('_atom_type_scat.', ['symbol', 'neutron_magnetic_source'])
        assert [(case.decoded(row[0]), row[1]) for row in table] == expected, (
            'Both saves keep each exact quoted-empty source in its keyed loop row, '
            'even if a notice was reported'
        )
        if saved == first:
            edi.Project.load(first).save_as(second)


@pytest.mark.parametrize('route', ['cli', 'app'])
def test_public_entrances_persist_both_quoted_empty_source_spellings(tmp_path, route):
    # Both are supplied text by the CIF grammar. Reading the raw saved cells
    # distinguishes quotes, bare missing markers and a dropped column.
    payload = case.STRUCTURE + (
        'loop_\n_atom_type_scat.symbol\n_atom_type_scat.neutron_magnetic_source\nBa \'\'\nO ""\n'
    )
    (result,) = observe(tmp_path, route, 'structure', [case.STRUCTURE, payload])
    assert 'refused' not in result, 'Both quoted-empty source spellings must be accepted'
    assert_quoted_empty_sources_on_two_saves(result['saved'], ('Ba', 'O'), ("''", '""'))


@pytest.mark.parametrize('route', ['cli', 'app'])
@pytest.mark.parametrize('kind', ['structure', 'experiment'])
def test_public_entrances_keep_cif_grammar_and_parser_refusals(tmp_path, route, kind):
    control = case.STRUCTURE if kind == 'structure' else case.EXPERIMENT
    wrapped = control.replace('_cell_length_a 5.1000', '_cell_length_a\n5.1000').replace(
        '10 21 2', '10\n21 2'
    )
    payloads = [control, wrapped, control + "_audit.note 'unterminated\n"]
    if kind == 'structure':
        payloads.append(control + 'loop_\n_atom_type_scat.neutron_magnetic_j0_A1\n0.271828\n')
    results = observe(tmp_path, route, kind, payloads)
    assert 'refused' not in results[0], 'The real public entrance accepts wrapped CIF tokens'
    assert 'refused' in results[1], (
        'The public entrance must refuse malformed CIF instead of retrying another reader'
    )
    assert results[1]['refused'], 'The public parser refusal retains its reason'
    if kind == 'structure':
        refusal = results[2].get('refused', '')
        assert case.notices(refusal, '_atom_type_scat.symbol') and 'atom-type key' in refusal, (
            'A coefficient loop without its atom-type key refuses at the named row key'
        )


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
