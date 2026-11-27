"""Exercise Python's Unicode paths across the native core boundary."""

import ctypes
import importlib
import os
import shutil
import unicodedata
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SCAN = ROOT / 'tests/fixtures/scan_template/project'


def test_python_paths_round_trip_through_save_import_and_scan(tmp_path, capsys):
    if os.name == 'nt' and ctypes.windll.kernel32.GetACP() not in {1252, 65001}:
        pytest.skip('This path fixture needs Windows cp1252 or UTF-8 to represent Université')
    edi = importlib.import_module('edi')
    folder = tmp_path / 'Université'
    folder.mkdir()
    data = folder / 'measured.xye'
    data.write_text('21.5 17.25 0.75\n22.75 31.75 1.25\n25.125 23.5 1.5\n', encoding='utf-8')
    experiment = edi.ExperimentFactory.from_data_path(
        name='pattern', data_path=str(data), beam_mode='constant wavelength'
    )
    assert list(experiment.data.intensity_meas) == [17.25, 31.75, 23.5], (
        'The native measured-data reader reaches the file under the exact Unicode path'
    )

    source = folder / 'imported.unicodepathcase'
    source.write_text('Input for the registered importer\n', encoding='utf-8')
    seen = []

    def convert(path):
        seen.append(path)
        return edi.Project(name='unicode_path')

    edi.register_project_importer('Unicode path witness', [source.suffix], convert)
    imported = edi.Project.load(source)
    assert seen == [str(source)], (
        'The Python importer receives the original readable absolute path'
    )
    saved = folder / 'Université'
    imported.save_as(saved)
    imported.save()
    # Use the names returned directly by the OS for a Unicode directory argument.
    listed = os.listdir(str(folder))  # noqa: PTH208
    listing = {unicodedata.normalize('NFC', name) for name in listed}
    assert saved.name in listing and 'UniversitÃ©' not in listing, (
        'The operating system lists the intended spelling without an alternate mojibake directory'
    )
    assert edi.Project.load(saved).name == imported.name, 'Python reopens the archive it saved'
    assert saved.name in capsys.readouterr().out, (
        'The native save message contains readable Unicode'
    )

    scan_dir = folder / 'scan'
    shutil.copytree(SCAN, scan_dir)
    scan = edi.Project.load(scan_dir)
    renamed_data = scan_dir / 'experiments' / 'd20_Université'
    (scan_dir / 'experiments' / 'd20_scan').rename(renamed_data)
    dataset = 'allUniversité.dat'
    (renamed_data / 'all594687.dat').rename(renamed_data / dataset)
    scan.analysis.sequential_fit.data_dir = 'experiments/d20_Université'
    scan.analysis.template_file = dataset
    assert scan.analysis.sequential_fit.data_dir == 'experiments/d20_Université', (
        'The scan directory getter returns the supplied path in Unicode'
    )
    assert scan.analysis.template_file == dataset, (
        'The scan template getter returns the dataset chosen by its Unicode filename'
    )


def test_python_refuses_a_path_cp1252_cannot_represent_before_creating_it(tmp_path):
    if os.name != 'nt' or ctypes.windll.kernel32.GetACP() != 1252:
        pytest.skip('A cp1252 Python process is needed for the ANSI refusal control')
    edi = importlib.import_module('edi')
    target = tmp_path / 'Łódź'
    project = edi.Project(name='refused')
    with pytest.raises(ValueError, match=r'Windows code page.*Łódź'):
        project.save_as(target)
    listed = os.listdir(str(tmp_path))  # noqa: PTH208
    assert not listed, (
        'Refusing before the native writer leaves the output parent empty'
    )
