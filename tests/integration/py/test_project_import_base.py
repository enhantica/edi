"""A further format joins through the public registry and ordinary Project.load."""

import uuid
from pathlib import Path

import edi
import pytest

NATIVE = Path(__file__).resolve().parents[2] / 'fixtures/constraint_expressions/project'


def test_registered_python_converter_receives_shared_naming_description_and_roundtrip(tmp_path):
    suffix = '.stub' + uuid.uuid4().hex
    source = tmp_path / ('sample-name' + suffix.upper())
    source.write_text('format witness', encoding='utf-8')
    called = []

    def convert(path):
        called.append(path)
        return edi.Project.load(NATIVE)

    edi.register_project_importer('PythonWitness', [suffix], convert)
    project = edi.Project.load(source)
    assert called == [str(source)], 'Project.load invokes only the registered Python conversion'
    assert project.name == 'sample-name', 'The common base names an import from its input stem'
    assert project.metadata.description == f'Imported from PythonWitness: {source.name}', (
        'A further program receives the common source description without writing its own loader'
    )
    edi.check_import_roundtrip(project, tmp_path / 'native')
    reopened = edi.Project.load(tmp_path / 'native')
    assert reopened.name == project.name, 'The public round-trip check writes an ordinary project'


def test_python_registration_cannot_replace_an_existing_suffix():
    with pytest.raises(ValueError, match=r'FullProf.*already reads.*pcr'):
        edi.register_project_importer('Duplicate', ['.PcR'], lambda _: edi.Project(name='unused'))


def test_builtin_importer_order_starts_with_cryspy():
    assert [program for program, _ in edi.project_importers()][:3] == [
        'cryspy',
        'FullProf',
        'GSAS-II',
    ], 'The importer registry follows the Load project order with cryspy first'
