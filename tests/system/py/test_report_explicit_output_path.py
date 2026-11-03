"Caller-selected HTML paths create missing parents without changing project bytes."

from pathlib import Path

import edi
import pytest

from tests.fixtures.constraint_expressions.project import materialize


def inventory(root):
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in root.rglob('*')
        if path.is_file()
    }


@pytest.mark.parametrize('saved', [False, True], ids=['unsaved', 'saved'])
@pytest.mark.parametrize('spelling', ['relative', 'absolute'])
@pytest.mark.parametrize('depth', [0, 1, 3], ids=['existing', 'one-missing', 'several-missing'])
def test_explicit_html_path_creates_every_missing_parent(
    tmp_path, monkeypatch, saved, spelling, depth
):
    source = materialize(tmp_path / 'project')
    project = edi.Project.load(source) if saved else edi.Project(name='unsaved_report')
    before = inventory(source)
    output = tmp_path / 'exports'
    output.mkdir()
    for index in range(depth):
        output /= f'level-{index}'
    path = output / 'explicit.html'
    monkeypatch.chdir(tmp_path)
    argument = path if spelling == 'absolute' else path.relative_to(tmp_path)
    expected = project.report.as_html(offline=False)
    written = project.report.save_html(argument, offline=False)
    assert Path(written).absolute() == path, (
        'Saving to an explicit HTML path returns that caller-selected path'
    )
    assert path.read_text() == expected and '<html' in expected, (
        'An explicit HTML path creates absent parents and writes the complete report'
    )
    assert inventory(source) == before, (
        'An explicit HTML export does not change any saved project bytes'
    )
    assert not list(output.glob('*.tmp')), (
        'A completed explicit report export leaves no temporary files'
    )


@pytest.mark.parametrize('saved', [False, True], ids=['unsaved', 'saved'])
@pytest.mark.parametrize('depth', [0, 2], ids=['linked-root', 'missing-under-linked-root'])
def test_explicit_html_parent_keeps_the_caller_selected_link_policy(tmp_path, saved, depth):
    source = materialize(tmp_path / 'project')
    project = edi.Project.load(source) if saved else edi.Project(name='unsaved_report')
    outside = tmp_path / 'selected-folder'
    outside.mkdir()
    sentinel = outside / 'unchanged'
    sentinel.write_bytes(b'independent caller-owned bytes\x00\n')
    link = tmp_path / 'chosen-link'
    link.symlink_to(outside, target_is_directory=True)
    parent = link
    for index in range(depth):
        parent /= f'new-{index}'
    expected = project.report.as_html(offline=False)
    project.report.save_html(parent / 'explicit.html', offline=False)
    assert link.is_symlink(), (
        'An explicit caller-selected external root link keeps its existing identity'
    )
    assert (parent / 'explicit.html').read_text() == expected, (
        'The explicit linked root receives the complete HTML report'
    )
    assert sentinel.read_bytes() == b'independent caller-owned bytes\x00\n', (
        'Export changes no sibling bytes in the caller-selected root'
    )
