"""red-first gates for edi's space-group coordinate-code wiring."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path

import edi
import pytest

from conftest import corpus_case_dir
from tests.model_calculation import calculate_on_grid

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / 'tests/fixtures/c12_t3_space_group_code'
ORACLE_PATH = FIXTURE / 'oracle.json'
ORACLE_SOURCE = FIXTURE / 'reflection_oracle.cpp'
ORACLE_GENERATOR = FIXTURE / 'generate.py'
SILICON_STRUCTURE = FIXTURE / 'si_origin_2.edi'
ABSORPTION_FIXTURE = ROOT / 'tests/fixtures/c09_t6_ncaf_5bank_absorption'
TYPE_NONE_PROJECT = ABSORPTION_FIXTURE / 'type_none_project'
NO_CODE_GOLDEN = ABSORPTION_FIXTURE / 'expected/desired_writer/no_code_type_none'


def _oracle() -> dict[str, object]:
    return json.loads(ORACLE_PATH.read_text(encoding='utf-8'))


def _tree_bytes(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob('*'))
        if path.is_file()
    }


def _complete_project() -> Path:
    return corpus_case_dir('ncaf-wish-3bank-s5') / 'project'


def _crysta_space_group_oracle() -> dict[str, object]:
    path = (
        corpus_case_dir('ncaf-wish-3bank-s5').parents[1]
        / 'system/fixtures/c12_t1_space_group_oracle.json'
    )
    return json.loads(path.read_text(encoding='utf-8'))


def _resolved_setting(it_number: int, code: str) -> dict[str, object]:
    matches = [
        record
        for record in _crysta_space_group_oracle()['records']
        if record['it_number'] == it_number and record['code'] == code
    ]
    assert len(matches) == 1, (
        'the independent cctbx-backed crysta oracle must identify exactly one requested setting'
    )
    return matches[0]


def _copy_complete_type_none_project(destination: Path) -> None:
    shutil.copytree(TYPE_NONE_PROJECT, destination)


def _copy_name_only_project(destination: Path) -> Path:
    shutil.copytree(NO_CODE_GOLDEN, destination)
    structure = destination / 'structures/ncaf.edi'
    lines = [
        line
        for line in structure.read_text(encoding='utf-8').splitlines()
        if not line.startswith(('_space_group.coord_system_code ', '_space_group.it_number '))
    ]
    structure.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    return structure


def _replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding='utf-8')
    assert text.count(old) == 1
    path.write_text(text.replace(old, new), encoding='utf-8')


def _owner_shape_project(tmp_path: Path, code: str | None = '2') -> Path:
    project = tmp_path / 'project'
    _copy_complete_type_none_project(project)
    shutil.rmtree(project / 'structures')
    (project / 'structures').mkdir()
    structure = project / 'structures/si.edi'
    text = SILICON_STRUCTURE.read_text(encoding='utf-8')
    if code is None:
        text = text.replace('_space_group.coord_system_code 2\n', '')
    elif code != '2':
        text = text.replace(
            '_space_group.coord_system_code 2', f'_space_group.coord_system_code {code}'
        )
    structure.write_text(text, encoding='utf-8')
    experiments = sorted((project / 'experiments').glob('*.edi'))
    assert len(experiments) == 1
    experiment = experiments[0]
    text = experiment.read_text(encoding='utf-8')
    replaced = re.sub(r'(?m)^ncaf (.+)$', r'si \1', text)
    assert replaced != text
    experiment.write_text(replaced, encoding='utf-8')
    return project


def _silicon_project(tmp_path: Path, code: str | None = '2'):
    project = edi.Project.load(_owner_shape_project(tmp_path, code))
    project.structure.scattering_lengths_fm = {'Si': float(_oracle()['silicon']['neutron_b_c_fm'])}
    return project


def test_c12_t3_fixture_and_direct_crysta_oracle_are_locked() -> None:
    oracle = _oracle()
    assert not ORACLE_SOURCE.exists(), 'the retired crysta reflection generator must stay absent'
    assert not ORACLE_GENERATOR.exists(), 'the retired oracle regeneration script must stay absent'
    assert oracle['schema'] == 1
    assert oracle['provenance'] == {
        'crysta_commit': '296e3ff2f17e9302c56141f80c7d279205a5eac6',
        'generator': 'reflection_oracle.cpp',
        'role': "direct crysta  setting oracle, independent of edi's  path",
        # Historical provenance: the generator was retired with crysta's reflections API, so its
        # frozen digest is the lock. Re-hashing a replacement would silently change the oracle's
        # independent source rather than protect these unchanged values.
        'generator_sha256': 'd50f3f08c390bcfcf15b8ab5dd5969ecfb3cfe017c0a86a140168f820a8fe34e',
        'symmetry_source': ' frozen cctbx.sgtbx oracle',
        'reflection_reference': 'International Tables F lattice: h,k,l all even or all odd',
    }, ' oracle provenance must stay anchored to merged crysta history'
    assert oracle['resolved_setting'] == {
        'it_number': 227,
        'coord_system_code': '2',
        'setting': 1,
        'hall': '-F 4vw 2vw 3',
        'operator_count': 192,
    }
    # Regression pin only: the structure fixture was mechanically rewritten to schema 2; the
    # direct-crysta reflection rows below remain the independent correctness oracle.
    assert (
        hashlib.sha256(SILICON_STRUCTURE.read_bytes()).hexdigest()
        == oracle['silicon']['structure_sha256']
    )
    structure = SILICON_STRUCTURE.read_text(encoding='utf-8')
    assert '_space_group.name_h_m "F d -3 m"' in structure
    assert '_space_group.coord_system_code 2' in structure
    assert 'Si1 Si 0.125 0.125 0.125 a 1 0 Biso' in structure


def test_c12_t3_complete_load_carries_it227_origin_2_code(
    tmp_path: Path,
) -> None:
    project = _silicon_project(tmp_path)
    oracle = _oracle()
    assert project.structure.space_group.name_h_m == 'F d -3 m', (
        'the complete load must retain the declared Hermann Mauguin name'
    )
    assert (
        project.structure.space_group.coord_system_code
        == oracle['resolved_setting']['coord_system_code']
    ), 'the complete load must retain the independently resolved setting code'


def test_c12_t3_ambiguous_name_without_code_keeps_both_candidates(
    tmp_path: Path,
) -> None:
    project = _silicon_project(tmp_path, code=None)
    assert not project.structure.space_group.coord_system_code
    with pytest.raises(ValueError, match=r'(?i)Hermann-Mauguin .* is ambiguous') as raised:
        calculate_on_grid(edi, project, [18000.0, 30000.0])
    message = str(raised.value)
    assert "(IT 227, code '1')" in message
    assert "(IT 227, code '2')" in message


def test_c12_t3_unknown_code_fails_closed_through_edi(tmp_path: Path) -> None:
    project = _silicon_project(tmp_path, code='3')
    with pytest.raises(ValueError, match=r'(?i)(space group|contradictory)') as raised:
        calculate_on_grid(edi, project, [18000.0, 30000.0])
    message = str(raised.value)
    assert 'contradictory' in message.lower()
    assert 'F d -3 m' in message
    assert "code '3'" in message


def test_c12_t3_unambiguous_name_with_wrong_code_fails_closed(tmp_path: Path) -> None:
    project_path = tmp_path / 'project'
    shutil.copytree(_complete_project(), project_path)
    _replace_once(
        project_path / 'structures/ncaf.edi',
        '_space_group.coord_system_code 1',
        '_space_group.coord_system_code 2',
    )
    project = edi.Project.load(project_path)
    with pytest.raises(ValueError, match=r'(?i)contradictory') as raised:
        calculate_on_grid(edi, project, [18000.0, 30000.0])
    message = str(raised.value)
    assert 'contradictory' in message.lower()
    assert 'I 21 3' in message
    assert "code '2'" in message


def test_c12_t3_writer_round_trip_preserves_name_and_code(tmp_path: Path) -> None:
    project = _silicon_project(tmp_path / 'source')
    destination = tmp_path / 'saved'
    project.save_as(destination)
    written = (destination / 'structures/si.edi').read_text(encoding='utf-8')
    assert '_space_group.name_h_m "F d -3 m"\n' in written
    assert '_space_group.coord_system_code 2\n' in written
    restored = edi.Project.load(destination)
    assert restored.structure.space_group.name_h_m == 'F d -3 m'
    assert restored.structure.space_group.coord_system_code == '2'


def test_e09_t58_resolved_identity_does_not_synthesize_unrelated_presence(
    tmp_path: Path,
) -> None:
    source = tmp_path / 'source-presence-control'
    structure_file = _copy_name_only_project(source)
    source_text = structure_file.read_text(encoding='utf-8')
    assert '_atom_site.adp_type' in source_text, (
        'F-d requires the canonical source to carry the model-held ADP type before the '
        'space-group identity is resolved'
    )
    project = edi.Project.load(source)
    assert all(site.adp_type == 'Biso' for site in project.structure.atom_sites), (
        'the presence control must begin with the ruled model-held ADP type'
    )
    destination = tmp_path / 'saved-presence-control'
    project.save_as(destination)
    written = (destination / 'structures/ncaf.edi').read_text(encoding='utf-8')
    source_tags = {line.split()[0] for line in source_text.splitlines() if line.startswith('_')}
    written_tags = {line.split()[0] for line in written.splitlines() if line.startswith('_')}
    assert written_tags - source_tags == {
        '_space_group.coord_system_code',
        '_space_group.it_number',
    }, (
        'the delegated crysta writer must synthesize exactly the engine-resolved identity fields: '
        'neither omit one nor widen persistence to unrelated model state'
    )
    assert '_atom_site.adp_type' in written, (
        'F-d requires delegated save to retain the unrelated model-held ADP type'
    )
    restored = edi.Project.load(destination)
    assert all(site.adp_type == 'Biso' for site in restored.structure.atom_sites), (
        'the unrelated model-held ADP type must survive the complete save-load round trip'
    )


def test_e09_t58_unresolved_space_group_fails_at_first_calculation(
    tmp_path: Path,
) -> None:
    source = tmp_path / 'unresolvable'
    structure_file = _copy_name_only_project(source)
    _replace_once(
        structure_file,
        '_space_group.name_h_m "I 21 3"',
        '_space_group.name_h_m "not a real space group"',
    )

    project = edi.Project.load(source)
    with pytest.raises(ValueError, match='not a real space group') as raised:
        calculate_on_grid(edi, project, [18000.0, 30000.0])
    message = str(raised.value)
    assert 'not a real space group' in message, (
        'the first calculation must retain the resolver diagnostic for the rejected identity'
    )
