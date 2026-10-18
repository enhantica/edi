"Every new project-output primitive is rejected outside the shared helper."

import hashlib
import json
from pathlib import Path

import pytest

from tests.system.py.project_output_source_scan import cpp_violations, python_violations, scan

ROOT = Path(__file__).resolve().parents[3]
CPP = [
    'std::ofstream out(path);',
    'using Sink = std::ofstream; Sink out(path);',
    'std::basic_ofstream<char> out(path);',
    'std::fstream out(path, std::ios::out);',
    'file.open(path, std::ios::app);',
    '::open(path, O_WRONLY | O_CREAT, 0600);',
    '_wopen(path, _O_WRONLY | _O_CREAT, 0600);',
    'FILE* f = fopen(path, "wb");',
    'auto fn = ::fopen; fn(path, "a");',
    'auto fn = ::open; fn(path, flags);',
    '::write(fd, data, size);',
    '::pwrite(fd, data, size, offset);',
    'fs::resize_file(path, 0);',
    '::unlinkat(fd, path, 0);',
    '::fwrite(data, 1, size, file);',
    'fs::remove(path);',
    'fs::remove_all(path);',
    'std::filesystem::rename(from, to);',
    'namespace alias = std::filesystem; alias::copy_file(a,b);',
    'namespace other = std::filesystem; other::copy(a,b);',
    'namespace output = std::filesystem; output::copy_file(a,b);',
    'using std::filesystem::remove; remove(path);',
    'auto fn = std::filesystem::rename; fn(from,to);',
    'QSaveFile file(path);',
    'file.open(QIODevice::WriteOnly);',
    'QFile::remove(path);',
    '#define PUBLISH(a,b) std::filesystem::rename(a,b)',
]
PYTHON = [
    'os.open(path, os.O_WRONLY | os.O_CREAT)',
    'shutil.move(source, target)',
    'path.symlink_to(target)',
    'path.hardlink_to(target)',
    'path.write_text(text)',
    'path.write_bytes(body)',
    'path.open("a")',
    'open(path, "wb")',
    'path.unlink()',
    'path.rename(target)',
    'path.replace(target)',
    'path.mkdir()',
    'shutil.copyfile(source, target)',
    'shutil.copytree(source, target)',
    'os.remove(path)',
    'from os import rename as move\nmove(source, target)',
    'sink = path.write_bytes\nsink(body)',
    'append = path.open\nappend("a")',
]


def test_project_output_sources_use_only_shared_output_helpers():
    assert not scan(), (
        'All project-output writes, appends, removals, renames and copies '
        'must pass through the explicit shared-helper allow-list: '
    ) + repr(scan())


@pytest.mark.parametrize('source', CPP, ids=[f'native-{i:02d}' for i in range(len(CPP))])
def test_every_native_output_primitive_and_alias_is_refused(source):
    assert cpp_violations(source), (
        'The mechanical source gate must reject each raw C++, C, '
        'filesystem, stream, Qt and alias spelling outside the helper'
    )


@pytest.mark.parametrize('source', PYTHON, ids=[f'python-{i:02d}' for i in range(len(PYTHON))])
def test_every_python_output_primitive_and_alias_is_refused(source):
    assert python_violations(source), (
        'The mechanical source gate must reject every raw Python file '
        'mutation and imported or assigned callable alias'
    )


@pytest.mark.parametrize(
    'source',
    [
        '#include <fstream>\nstd::ifstream in(path);',
        'auto text = "std::ofstream out(path)"; // fs::remove(path);',
        '/* fs::rename(from,to); */ crysta::output::copy_file(a,b);',
        'namespace safe = crysta::output; safe::copy_file(a,b);',
        '::open(path, O_RDONLY);',
        'fopen(path, "rb");',
        ('std::fprintf(stderr, "%s", text); std::fputs(text, stdout); std::fflush(stderr);'),
    ],
    ids=[
        'input-stream',
        'literal',
        'comment',
        'helper-alias',
        'read-open',
        'read-fopen',
        'diagnostics',
    ],
)
def test_reads_comments_literals_diagnostics_and_helper_calls_remain_valid(source):
    assert not cpp_violations(source), (
        'Read-only input, text literals, diagnostics and calls to the '
        'declared shared helper remain valid'
    )


@pytest.mark.parametrize(
    'source',
    [
        'path.read_text()',
        'path.open("rb")',
        'text.replace("a", "b")',
        'sys.stderr.write("diagnostic")',
    ],
    ids=['read-text', 'read-open', 'text-replacement', 'diagnostics'],
)
def test_python_read_and_diagnostic_controls_remain_valid(source):
    assert not python_violations(source), (
        'Python read-only input, string replacement and standard '
        'diagnostics remain outside project file mutation'
    )


def test_new_output_source_is_scanned_and_only_the_named_helper_is_allowed(tmp_path):
    contract = json.loads((ROOT / 'tests/fixtures/project_output/contract.json').read_text())
    for name in contract['project_output']:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('')
    helper = tmp_path / contract['helpers'][0]
    helper.parent.mkdir(parents=True, exist_ok=True)
    helper.write_text(
        'path.write_bytes(body)' if helper.suffix == '.py' else 'std::ofstream out(path);'
    )
    assert not scan(tmp_path), 'The exact declared shared helper owns raw output operations'
    fresh = tmp_path / contract['roots'][0] / 'new_project_writer.cpp'
    fresh.parent.mkdir(parents=True, exist_ok=True)
    fresh.write_text('std::ofstream out(path);')
    assert any(name.endswith('new_project_writer.cpp') for name, _ in scan(tmp_path)), (
        'Adding a new production source cannot escape the output scan through an unlisted filename'
    )
    helper.with_name('project_output_extra.cpp').write_text('std::ofstream out(path);')
    assert any(name.endswith('project_output_extra.cpp') for name, _ in scan(tmp_path)), (
        'The helper allow-list is exact rather than a filename-prefix exemption'
    )


def test_user_selected_result_exception_cannot_hide_an_additional_writer():
    source = 'void write_results(Args args) { std::ofstream out(args.out); }'
    assert not cpp_violations(source, {'write_results'}), (
        'The existing user-selected result stream remains outside project output'
    )
    escaped = source[:-1] + ' std::ofstream extra(project); }'
    assert cpp_violations(escaped, {'write_results'}), (
        'The result exception covers only its exact user-output open '
        'and cannot exempt another writer in that function'
    )


def test_output_contract_keeps_its_exact_scope_and_helper_allow_list():
    folder = ROOT / 'tests/fixtures/project_output'
    contract = json.loads((folder / 'contract.json').read_text())
    assert contract == {
        'roots': ['core/src', 'app/src', 'lib/edi', 'core/include'],
        'project_output': [
            'core/src/report_save.cpp',
            'app/src/scan_session.cpp',
            'lib/edi/__init__.py',
            'lib/edi/__main__.py',
        ],
        'helpers': ['lib/edi/_project_output.py'],
        'namespace': 'crysta::output',
    }, (
        'The source boundary retains its reviewed roots, project '
        'outputs and exact helper allow-list'
    )
    # Regression pin for the pre-helper non-output source inventory, not a scientific oracle.
    assert (
        hashlib.sha256((folder / 'source_inventory.json').read_bytes()).hexdigest()
        == '266697d5c28e3cfb9528bbbb173d45325af3203f287a77942d31b97baad604c3'
    ), 'The pre-helper source inventory cannot silently exempt a new output writer'
