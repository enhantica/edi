"""Project archives interoperate with Python's independent ZIP reader and writer."""

import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import edi
import pytest

ROOT = Path(__file__).resolve().parents[3]
CASES = (
    'sc-neut-tof_taurine_fit',
    'pd-neut-cwl_cosio-d20_scan-3f',
    'sc-neut-cwl_tb2ti2o7-heidi_basic',
)


def inventory(root):
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob('*')
        if path.is_file()
    }


def source(tmp_path, case):
    result = tmp_path / 'source'
    shutil.copytree(ROOT / 'docs/user/cli' / case / 'project', result)
    reports = result / 'reports'
    reports.mkdir(exist_ok=True)
    (reports / 'opaque.html').write_bytes(b'<p>Independently authored report: \xce\xb1</p>\n')
    return result


def cli(*args):
    return subprocess.run(
        [sys.executable, '-m', 'edi', *map(str, args)],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )


@pytest.mark.parametrize('case', CASES)
@pytest.mark.parametrize('surface', ['python', 'cli'])
def test_exports_contain_the_complete_project_and_reports_without_caches(tmp_path, case, surface):
    folder = source(tmp_path, case)
    expected = inventory(folder)
    for relative in ('build/object.o', '.cache/state', '__pycache__/module.pyc', '.pixi/state'):
        path = folder / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'not project content\n')
    before = inventory(folder)
    archive = tmp_path / 'export.zip'
    if surface == 'python':
        project = edi.Project.load(folder)
        assert callable(getattr(project, 'export_zip', None)), (
            'Python Project.export_zip exposes the shared core project archive writer'
        )
        project.export_zip(archive)
    else:
        result = cli('export', folder, '-o', archive)
        assert result.returncode == 0, (
            'The export command writes a complete project archive: ' + result.stderr
        )
    with zipfile.ZipFile(archive) as opened:
        names = opened.namelist()
        assert len(names) == len(set(names)), 'A project archive contains each member exactly once'
        actual = {name: opened.read(name) for name in names if not name.endswith('/')}
    assert actual == expected, (
        'Every project and report member retains its exact folder bytes; '
        'build and cache files are excluded'
    )
    assert inventory(folder) == before, 'Export never changes the source project or report bytes'


@pytest.mark.parametrize('case', CASES)
@pytest.mark.parametrize('route', ['folder', 'project.edi', 'zip'])
def test_python_opens_each_project_route_and_preserves_model_values(tmp_path, case, route):
    folder = source(tmp_path, case)
    archive = tmp_path / 'independent.zip'
    with zipfile.ZipFile(archive, 'w', zipfile.ZIP_DEFLATED) as output:
        for name, body in inventory(folder).items():
            output.writestr(name, body)
    path = {'folder': folder, 'project.edi': folder / 'project.edi', 'zip': archive}[route]
    expected = edi.Project.load(folder)
    loaded = edi.Project.load(path)
    assert loaded.name == expected.name, 'Every open route preserves the declared project identity'
    assert [s.name for s in loaded.structures] == [s.name for s in expected.structures], (
        'Folder, project record and ZIP routes preserve every structure and its order'
    )
    for actual, original in zip(loaded.structures, expected.structures, strict=True):
        for field in (
            'length_a',
            'length_b',
            'length_c',
            'angle_alpha',
            'angle_beta',
            'angle_gamma',
        ):
            assert getattr(actual.cell, field).value == getattr(original.cell, field).value, (
                'Archive opening preserves every independently loaded cell value exactly'
            )
    if route == 'zip':
        # The owner reversed the former first-Save-as rule: Save now writes the opened ZIP.
        before = archive.read_bytes()
        loaded.metadata.name = 'zip-python-save'
        loaded.save()
        assert archive.read_bytes() != before, 'Saving an edit rewrites the same opened ZIP'
        assert edi.Project.load(archive).name == 'zip-python-save', (
            'Reopening the same ZIP preserves the Python edit written by ordinary Save'
        )
        with zipfile.ZipFile(archive) as written:
            assert (
                written.read('reports/opaque.html') == inventory(folder)['reports/opaque.html']
            ), 'Ordinary ZIP write-back retains every independently authored report byte'
        destination = tmp_path / 'kept'
        loaded.save_as(destination)
        assert Path(loaded.metadata.path) == destination, (
            'First Save as establishes the project folder'
        )
        assert (destination / 'reports/opaque.html').read_bytes() == inventory(folder)[
            'reports/opaque.html'
        ], 'Saving an archive-opened project retains its carried report bytes'
        loaded.save()
        assert edi.Project.load(destination).name == 'zip-python-save', (
            'Later Save writes the established project folder'
        )


@pytest.mark.parametrize('case', CASES)
def test_cli_calculation_opens_an_independently_created_zip_without_overwriting_it(tmp_path, case):
    folder = source(tmp_path, case)
    archive = tmp_path / 'independent.zip'
    with zipfile.ZipFile(archive, 'w') as output:
        for name, body in inventory(folder).items():
            output.writestr(name, body)
    before = archive.read_bytes()
    result = cli('calc', archive, '--dry', '--verbosity', 'off')
    assert result.returncode == 0, 'CLI calculation accepts a project ZIP path: ' + result.stderr
    assert archive.read_bytes() == before, 'A ZIP input is never the CLI write-back destination'


@pytest.mark.parametrize(
    'member',
    [
        '../escaped.edi',
        'nested/../../escaped.edi',
        '/escaped.edi',
        '..\\escaped.edi',
        'C:/escaped.edi',
    ],
)
@pytest.mark.parametrize('surface', ['python', 'cli'])
def test_every_archive_reader_refuses_a_member_outside_its_project(tmp_path, member, surface):
    folder = source(tmp_path, CASES[2])
    archive = tmp_path / 'hostile.zip'
    with zipfile.ZipFile(archive, 'w') as output:
        for name, body in inventory(folder).items():
            output.writestr(name, body)
        output.writestr(member, b'outside project\n')
    before = inventory(tmp_path)
    if surface == 'python':
        with pytest.raises((ValueError, RuntimeError, OSError)) as error:
            edi.Project.load(archive)
        assert any(
            word in str(error.value).lower()
            for word in ('path', 'archive', 'zip', 'outside', 'entry')
        ), 'Archive containment refusals explain the invalid ZIP entry'
    else:
        result = cli('calc', archive, '--dry', '--verbosity', 'off')
        assert result.returncode != 0, 'The CLI refuses an archive containing an escaping member'
        assert any(
            word in result.stderr.lower()
            for word in ('path', 'archive', 'zip', 'outside', 'entry')
        ), 'The CLI reports archive containment rather than attempting a project calculation'
    assert inventory(tmp_path) == before, (
        'Refusing an archive publishes no extracted outside bytes'
    )
