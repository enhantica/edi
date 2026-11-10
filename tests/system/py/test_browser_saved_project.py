"""Browser protocol counterfactuals; actual packed-kit runs remain required for UI claims."""

import shutil
import stat
import subprocess
import zipfile
from pathlib import Path

import pytest

from tests.fixtures.e04_t11_wasm.reopen import archive_files, assert_documents

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize(
    'script', ['web_saved_fit_controls.mjs', 'web_control_geometry_controls.mjs']
)
def test_saved_browser_reference_and_real_row_refuse_wrong_operands(script):
    node = shutil.which('node')
    assert node, 'Browser protocol controls must execute with the declared Node runtime'
    run = subprocess.run(
        [node, str(ROOT / 'tests/system/manual' / script)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=4,
        check=False,
    )
    assert run.returncode == 0, (
        'Actual browser helpers must refuse wrong project, scientific and row-geometry operands: '
        + run.stdout
        + run.stderr
    )


def test_reopened_project_preserves_inputs_and_checks_the_written_model_calculation():
    project = b'_metadata.name sample\n_metadata.last_modified "yesterday"\n'
    structure = (
        b'loop_\n_atom_site.id\n_atom_site.fract_x\n_atom_site.fract_y\n'
        b'Al1 0.2520(3) 0.2519537810264925\n'
        b'_cell.length_a 10.250256\n_cell.length_b 10.2502559999999\n'
    )
    experiment = (
        b'_instrument.calib_d_to_tof_linear 4985.3(9)\n'
        b'loop_\n_data.id\n_data.intensity_meas\n_data.intensity_calc\n_data.calc_status\n'
        b'1 831.5585 760.5952590779875 incl\n'
    )
    before = {
        'project.edi': project,
        'analysis/analysis.edi': b'_fit_result.success true\n_fit_result.iterations 5\n',
        'structures/sample.edi': structure,
        'experiments/sample.edi': experiment,
        'README.md': b'Keep the project notes.\n',
    }
    expected = {
        **before,
        'structures/sample.edi': structure.replace(b'0.2519537810264925', b'0.252').replace(
            b'10.2502559999999', b'10.250256'
        ),
        'experiments/sample.edi': experiment.replace(b'760.5952590779875', b'761.25'),
    }
    after = {**expected, 'project.edi': project.replace(b'yesterday', b'today')}
    assert_documents(before, after, expected)
    changes = [
        ('project.edi', b'sample', b'other'),
        ('analysis/analysis.edi', b'iterations 5', b'iterations 6'),
        ('structures/sample.edi', b'0.2520(3)', b'0.2521(3)'),
        ('structures/sample.edi', b'0.2520(3)', b'0.2520(4)'),
        ('structures/sample.edi', b'0.252\n', b'0.253\n'),
        ('structures/sample.edi', b'10.250256', b'10.250257'),
        ('structures/sample.edi', b'Al1', b'Al2'),
        ('experiments/sample.edi', b'4985.3(9)', b'4985.4(9)'),
        ('experiments/sample.edi', b'831.5585', b'831.5586'),
        ('experiments/sample.edi', b'761.25', b'762.25'),
        ('experiments/sample.edi', b'761.25', b'nan'),
        ('experiments/sample.edi', b'1 831', b'2 831'),
        ('experiments/sample.edi', b'incl', b'excl'),
        ('README.md', b'notes', b'changes'),
    ]
    for name, old, new in changes:
        assert old in after[name], 'Every reopen escape must reach a saved-field operand'
        damaged = {**after, name: after[name].replace(old, new)}
        with pytest.raises(AssertionError):
            assert_documents(before, damaged, expected)
    for name in after:
        with pytest.raises(AssertionError):
            assert_documents(
                before, {key: value for key, value in after.items() if key != name}, expected
            )
    with pytest.raises(AssertionError):
        assert_documents(before, {**after, 'extra.edi': b'extra'}, expected)
    with pytest.raises(AssertionError):
        assert_documents(before, before, expected)


@pytest.mark.parametrize('prefix', ['', 'owned/'])
def test_saved_archive_flat_and_nested_owners_retain_every_file_byte(tmp_path, prefix):
    archive = tmp_path / 'owned.zip'
    files = {
        'project.edi': b'_edi.schema_version 3\n_metadata.last_modified today\n',
        'analysis/analysis.edi': b'_fit_result.success true\n',
        'structures/sample.edi': b'data_sample\n_cell.length_a 2.125(3)\n',
        'experiments/bank.edi': b'data_bank\nloop_\n_data.id\n_data.calc_status\n1 excl\n',
        'README.md': b'Keep the notes and every opaque byte.\n',
        'assets/opaque.bin': b'\x00\xffopaque\r\n',
    }
    with zipfile.ZipFile(archive, 'w') as writer:
        if prefix:
            writer.writestr(prefix, b'')
        writer.writestr(prefix + 'assets/', b'')
        for name, contents in files.items():
            writer.writestr(prefix + name, contents)
    assert archive_files(archive) == files, (
        'Required: saved archive flat and nested owners retain every file byte.'
    )
    with zipfile.ZipFile(archive, 'a') as writer:
        writer.writestr(prefix + 'extra.bin', b'An extra file must not be silently ignored.')
    assert archive_files(archive) == {
        **files,
        'extra.bin': b'An extra file must not be silently ignored.',
    }, 'Required: saved archive flat and nested owners retain every file byte.'


@pytest.mark.parametrize(
    'members',
    [
        [('notes.txt', b'no root')],
        [('notproject.edi', b'not a project')],
        [('project.edi', b'flat'), ('nested/project.edi', b'nested')],
        [('one/project.edi', b'one'), ('two/project.edi', b'two')],
        [('owner/project.edi', b'owner'), ('outside.bin', b'outside')],
        [('owner/project.edi', b'owner'), ('owner-neighbor/file.bin', b'outside')],
        [('project.edi', b'flat'), ('../escape.bin', b'escape')],
        [('owner/project.edi', b'owner'), ('owner/../escape.bin', b'escape')],
        [('project.edi', b'flat'), ('/absolute.bin', b'absolute')],
        [('project.edi', b'flat'), ('C:/absolute.bin', b'drive')],
        [('project.edi', b'flat'), ('C:relative.bin', b'drive-relative')],
        [('project.edi', b'flat'), ('bad\\path.bin', b'backslash')],
        [('project.edi', b'flat'), ('./alias.bin', b'alias')],
        [('project.edi', b'flat'), ('folder//alias.bin', b'alias')],
        [('project.edi', b'flat'), ('folder', b'file'), ('folder/child.bin', b'child')],
        [('project.edi', b'flat'), ('folder/', b''), ('folder', b'file')],
    ],
)
def test_saved_archive_ambiguous_or_unsafe_members_refuse(tmp_path, members):
    archive = tmp_path / 'owned-negative.zip'
    with zipfile.ZipFile(archive, 'w') as writer:
        for name, contents in members:
            # Preserve the literal bad name even on hosts whose ZipInfo constructor
            # would translate their native separator before writing the test archive.
            member = zipfile.ZipInfo('literal-member')
            member.filename = name
            member.orig_filename = name
            writer.writestr(member, contents)
    with pytest.raises(AssertionError):
        archive_files(archive)


@pytest.mark.parametrize('prefix', ['', 'owned/'])
@pytest.mark.parametrize('target', ['project.edi', 'assets/blob.bin'])
def test_saved_archive_duplicate_path_refuses(tmp_path, prefix, target):
    archive = tmp_path / 'owned-duplicate.zip'
    with zipfile.ZipFile(archive, 'w') as writer:
        writer.writestr(prefix + 'project.edi', b'project')
        if target != 'project.edi':
            writer.writestr(prefix + target, b'first')
        with pytest.warns(UserWarning, match='Duplicate name'):
            writer.writestr(prefix + target, b'second')
    with zipfile.ZipFile(archive) as planted:
        assert planted.namelist().count(prefix + target) == 2, (
            'Required: saved archive duplicate path refuses.'
        )
    expected = 'exactly one project root' if target == 'project.edi' else 'duplicate'
    with pytest.raises(AssertionError, match=expected):
        archive_files(archive)


@pytest.mark.parametrize('target', ['project.edi', 'assets/link.bin', 'assets/link/'])
def test_saved_archive_encoded_symlink_refuses_even_inside_flat_owner(tmp_path, target):
    archive = tmp_path / 'owned-link.zip'
    link = zipfile.ZipInfo(target)
    link.create_system = 3
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(archive, 'w') as writer:
        if target != 'project.edi':
            writer.writestr('project.edi', b'project')
        writer.writestr(link, b'../../outside')
    with pytest.raises(AssertionError, match='symbolic links'):
        archive_files(archive)
