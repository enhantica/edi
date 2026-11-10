""": edi delegates the actual model's extract identities to the writer."""

import edi
import test_c13_t12_loop_identity as loops
from c13_t12_support import tokens


def test_writer_delegates_actual_project_to_shared_engine_encoder(tmp_path):
    loops._load(tmp_path / 'input', 'sequential_fit_extract', 'project')
    analysis = tmp_path / 'input/analysis/analysis.edi'
    analysis.write_text('_sequential_fit.data_dir scan\n' + analysis.read_text())
    scan = tmp_path / 'input/scan'
    scan.mkdir()
    (scan / 'point.txt').write_text('TEMP 123\n')

    model = edi.Project.load(tmp_path / 'input')
    model.save_as(tmp_path / 'published')
    lexemes = tokens((tmp_path / 'published/analysis/analysis.edi').read_text())
    header = next(i for i, token in enumerate(lexemes) if token[0] == '_sequential_fit_extract.id')
    columns = []
    while lexemes[header][0].startswith('_sequential_fit_extract.'):
        columns.append(lexemes[header][0])
        header += 1
    assert columns == [
        '_sequential_fit_extract.id',
        '_sequential_fit_extract.target',
        '_sequential_fit_extract.pattern',
        '_sequential_fit_extract.required',
    ], ' the published extract loop must retain its declared columns'
    rows = [tuple(token[1] for token in lexemes[header + i : header + i + 4]) for i in (0, 4)]
    assert rows == [
        ('t17', 'temperature', '(.*)', 'true'),
        ('t93', 'pressure', '(.*)', 'false'),
    ], ' both decoded extract identities and companions must reach the published project'
