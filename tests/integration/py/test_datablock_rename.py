"""The owner's rename/save reproduction, using declared input identities."""

import shlex
import shutil
from pathlib import Path

import edi
import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.parametrize(
    ('kind', 'old', 'new', 'target'),
    [
        ('structure', 'lbco', 'structure1', 'lbco.atom_site.La.adp_iso'),
        ('experiment', 'hrpt', 'experiment1', 'hrpt.instrument.calib_twotheta_offset'),
    ],
)
def test_datablock_alias_rename_saves_and_reopens(tmp_path, kind, old, new, target):
    source = tmp_path / 'source'
    shutil.copytree(ROOT / 'tests/fixtures/e04_t1/editable-project', source)
    analysis = source / 'analysis/analysis.edi'
    analysis.write_text(
        analysis.read_text()
        + '\nloop_\n_alias.id\n_alias.parameter_unique_name\n'
        + 'alias_1 '
        + target
        + '\n'
    )
    project = edi.Project.load(source)
    blocks = project.structures if kind == 'structure' else project.experiments
    blocks[old].name = new
    destination = tmp_path / 'renamed'
    project.save_as(destination)
    text = (destination / 'analysis/analysis.edi').read_text()
    expected = new + target[len(old) :]
    assert expected in shlex.split(text), 'Save must persist the alias under its renamed datablock'
    for path in destination.rglob('*.edi'):
        tokens = shlex.split(path.read_text())
        assert not any(token == old or token.startswith(old + '.') for token in tokens), (
            'Every saved category must be free of references to the old datablock identity'
        )
    assert (destination / (kind + 's') / (new + '.edi')).is_file(), (
        'The renamed block must have its own correctly named .edi file'
    )
    reopened = edi.Project.load(destination)
    saved_again = tmp_path / 'reopened'
    reopened.save_as(saved_again)
    assert (saved_again / 'analysis/analysis.edi').read_bytes() == (
        destination / 'analysis/analysis.edi'
    ).read_bytes(), 'Reopening and saving must preserve the rewritten alias category exactly'
