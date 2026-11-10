"""Observe real notebook fits with an offline collection; never supply fitted answers."""

import importlib.util
import json
import os
from contextlib import contextmanager

import nbformat
from nbclient import NotebookClient

from tests.fixtures.tutorial_cases.contract import ROOT
from tests.fixtures.tutorial_cases.presentation import text

PRELUDE = """import json as _stage_json, socket as _stage_socket
import easydiffraction as _stage_edi
_stage_original_fit = _stage_edi.Analysis.fit
_stage_fits = []
def _stage_record_fit(self, *args, **kwargs):
    before_json = self._project.report.model(excluded=['data', 'reflections']).to_json()
    before = _stage_json.loads(before_json)
    result = _stage_original_fit(self, *args, **kwargs)
    raw = self._project.report.model(excluded=['data', 'reflections']).to_json()
    document = _stage_json.loads(raw)
    machine = _stage_edi.machine_report(self._project, result, _stage_edi.VerbosityEnum.FULL)
    _stage_fits.append({'machine': machine, 'before': before['parameters'],
                       'correlations': document['correlations'],
                       'parameters': document['parameters']})
    return result
_stage_edi.Analysis.fit = _stage_record_fit
_stage_original_lookup = _stage_socket.getaddrinfo
def _stage_offline_lookup(host, *args, **kwargs):
    if host not in ('localhost', '127.0.0.1', '::1', None):
        raise RuntimeError('Tutorial tried an external network host: ' + str(host))
    return _stage_original_lookup(host, *args, **kwargs)
_stage_socket.getaddrinfo = _stage_offline_lookup
"""
POSTLUDE = "print('TUTORIAL_FIT_WITNESS ' + _stage_json.dumps(_stage_fits))"


@contextmanager
def environment(values):
    previous = {name: os.environ.get(name) for name in values}
    os.environ.update(values)
    try:
        yield
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value


def local_collection(destination):
    spec = importlib.util.spec_from_file_location(
        'tutorial_collection_builder', ROOT / 'tools/data/build_collection.py'
    )
    builder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(builder)
    assert builder.populate(destination) == 0 and builder.index(destination) == 0, (
        'Gate 3: the real collection producer supplies local inputs without a remote transport'
    )
    return destination


def execute(case, folder, collection):
    source = json.loads((ROOT / 'docs/user/tutorials' / (case + '.ipynb')).read_text())
    cells = []
    for original in source['cells']:
        if original['cell_type'] == 'code' and '%pip install ' in text(original):
            continue  # The guarded installation has its independent package gate.
        cell = dict(original)
        cell['source'] = text(original)
        if cell['cell_type'] == 'code':
            cell.update(outputs=[], execution_count=None)
        cells.append(cell)
    source['cells'] = [
        nbformat.v4.new_code_cell(PRELUDE),
        *cells,
        nbformat.v4.new_code_cell(POSTLUDE),
    ]
    notebook = nbformat.from_dict(source)
    folder.mkdir()
    with environment({
        'EDI_COLLECTION': str(collection),
        'EDI_SOURCE_BUILD': '1',
        'OMP_NUM_THREADS': '1',
        'OPENBLAS_NUM_THREADS': '1',
    }):
        NotebookClient(
            notebook,
            kernel_name='python3',
            timeout=3600,
            resources={'metadata': {'path': str(folder)}},
        ).execute()
    nbformat.write(notebook, folder / 'run-with-observer.ipynb')
    output = ''.join(str(item.get('text', '')) for item in notebook.cells[-1].outputs)
    prefix = 'TUTORIAL_FIT_WITNESS '
    lines = [line[len(prefix) :] for line in output.splitlines() if line.startswith(prefix)]
    assert len(lines) == 1, 'Gate 3: the actual notebook kernel returns one raw final-fit witness'
    records = json.loads(lines[0])
    assert len(records) >= 2, 'Gate 3: the real notebook executes more than one actual fit stage'
    first = {row['unique_name'] for row in records[0]['before'] if row['free']}
    assert any(
        {row['unique_name'] for row in record['before'] if row['free']} - first
        for record in records[1:]
    ), 'Gate 3: actual model flags free further parameters after the first fit'
    (folder / 'fit-witness.json').write_text(json.dumps(records, indent=2) + '\n')
    return records
