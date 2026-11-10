"""Execute unchanged notebook cells in the explicitly selected clean wheel kernel."""

import argparse
import json
import sys
from pathlib import Path

import nbformat
from nbclient import NotebookClient

PRELUDE = """import importlib.metadata as _clean_md
import importlib.util as _clean_util
import json as _clean_json
import pathlib as _clean_path
import socket as _clean_socket
import sys as _clean_sys
from packaging.requirements import Requirement as _clean_Requirement
from packaging.utils import canonicalize_name as _clean_name


def _clean_witness(roots):
    prefix = _clean_path.Path(_clean_sys.prefix).resolve()
    assert prefix == _clean_path.Path(_clean_expected).resolve(), (
        'Clean wheel kernel uses its fresh environment'
    )
    assert not any(
        'site-packages' in entry and not _clean_path.Path(entry).resolve().is_relative_to(prefix)
        for entry in _clean_sys.path
    ), 'Clean wheel kernel cannot see host site packages'
    installed = {_clean_name(row.metadata['Name']) for row in _clean_md.distributions()}
    allowed, pending = set(), list(roots)
    while pending:
        name = _clean_name(pending.pop())
        if name in allowed:
            continue
        allowed.add(name)
        for raw in _clean_md.requires(name) or []:
            requirement = _clean_Requirement(raw)
            if requirement.marker is None or requirement.marker.evaluate({'extra': ''}):
                pending.append(requirement.name)
    assert not installed - allowed, (
        'Clean wheel environment holds only declared wheel and Jupyter dependencies'
    )
    return {
        'prefix': str(prefix),
        'installed': sorted(installed),
        'allowed': sorted(allowed),
        'sys_path': list(_clean_sys.path),
        'executable': _clean_sys.executable,
    }


assert _clean_util.find_spec('easydiffraction') is None, (
    "The notebook's own install cell installs the built wheel"
)
print('CLEAN_START ' + _clean_json.dumps(_clean_witness(['pip', 'ipykernel', 'nbclient'])))
_clean_lookup = _clean_socket.getaddrinfo


def _clean_offline(host, *args, **kwargs):
    if host not in ('localhost', '127.0.0.1', '::1', None):
        raise RuntimeError('Offline notebook attempted external transport: ' + str(host))
    return _clean_lookup(host, *args, **kwargs)


_clean_socket.getaddrinfo = _clean_offline
"""
POSTLUDE = """import easydiffraction as _clean_edi

_clean_final = _clean_witness(['pip', 'ipykernel', 'nbclient', 'easydiffraction'])
_clean_origins = {
    name: str(_clean_path.Path(module.__dict__['__file__']).resolve())
    for name, module in _clean_sys.modules.items()
    if (name in ('edi', 'easydiffraction') or name.startswith('edi.'))
    and module.__dict__.get('__file__')
}
assert {'edi', 'easydiffraction'} <= set(_clean_origins), (
    'The public facade and implementation are loaded from the wheel'
)
assert all(
    _clean_path.Path(path).is_relative_to(_clean_path.Path(_clean_sys.prefix).resolve())
    for path in _clean_origins.values()
), 'Every edi Python/native module comes from the installed wheel'
assert any(path.endswith(('.so', '.pyd')) for path in _clean_origins.values()), (
    'The wheel contains the actual native extension'
)
_clean_final['origins'] = _clean_origins
print('CLEAN_FINISH ' + _clean_json.dumps(_clean_final))
"""


def witness(cell, prefix):
    rows = [
        line[len(prefix) :]
        for output in cell.get('outputs', [])
        for line in str(output.get('text', '')).splitlines()
        if line.startswith(prefix)
    ]
    return json.loads(rows[0]) if len(rows) == 1 else None


def run(source, output, kernel):
    original = nbformat.read(source, as_version=4)
    for cell in original.cells:
        if cell.cell_type == 'code':
            cell.update(outputs=[], execution_count=None)
    document = nbformat.from_dict(dict(original))
    document.cells = [
        nbformat.v4.new_code_cell('_clean_expected = ' + repr(sys.prefix) + '\n' + PRELUDE),
        *original.cells,
        nbformat.v4.new_code_cell(POSTLUDE),
    ]
    result = {'passed': False, 'phase': 'kernel', 'source': str(source)}
    try:
        NotebookClient(
            document,
            kernel_name=kernel,
            timeout=900,
            force_raise_errors=True,
            resources={'metadata': {'path': str(output)}},
        ).execute()
        unrun = [
            index
            for index, cell in enumerate(document.cells[1:-1])
            if cell.cell_type == 'code' and cell.source.strip() and cell.execution_count is None
        ]
        assert not unrun, 'Gate 3/6: every original nonempty tutorial cell actually executes'
        result.update(passed=True, phase='complete')
    except Exception as error:  # noqa: BLE001 - retain every case failure and continue the census
        result.update(error_type=type(error).__name__, error=str(error)[-12000:])
    result['start'] = witness(document.cells[0], 'CLEAN_START ')
    result['finish'] = witness(document.cells[-1], 'CLEAN_FINISH ')
    nbformat.write(document, output / 'run-with-environment-witness.ipynb')
    (output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
    return 0 if result['passed'] else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source', type=Path)
    parser.add_argument('output', type=Path)
    parser.add_argument('--kernel', default='edi-wheel-clean')
    args = parser.parse_args()
    return run(args.source, args.output, args.kernel)


if __name__ == '__main__':
    sys.exit(main())
