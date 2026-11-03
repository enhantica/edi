"""Check saved-model bytes and a native calculation from their written precision."""

import math
import re
import sys
import tempfile
import zipfile
from pathlib import Path

import edi

TOKEN = re.compile(rb'"[^"\n]*"|\'[^\'\n]*\'|[^ \t\r\n]+')
DEPENDENTS = {'_atom_site.fract_' + axis for axis in 'xyz'}
DEPENDENTS.update('_cell.length_' + axis for axis in 'abc')
DEPENDENTS.update('_cell.angle_' + angle for angle in ('alpha', 'beta', 'gamma'))
DERIVED = {
    '_data.d_spacing',
    '_data.intensity_calc',
    '_data.intensity_bkg',
    '_geom_bond.distance',
    '_geom_angle.angle',
}
DERIVED.update(
    '_expanded_atom_site.' + field
    for field in ('fract_x', 'fract_y', 'fract_z', 'cartn_x', 'cartn_y', 'cartn_z', 'u_iso')
)
DERIVED.update(
    '_refln.' + field
    for field in (
        'd_spacing',
        'sin_theta_over_lambda',
        'f_calc',
        'f_squared_calc',
        'time_of_flight',
        'two_theta',
    )
)
DERIVED.update(
    '_atom_sites_cartn_transform.mat_' + str(i) + str(j) for i in range(1, 4) for j in range(1, 4)
)


def projection(data, predicted=None):
    """Mask only calculated numeric fields; retain whitespace and every input token."""
    names, values, lines = [], [], []
    predicted_values = iter(predicted) if predicted is not None else None
    for raw in data.splitlines(keepends=True):
        line = raw
        tokens = list(TOKEN.finditer(line))
        if not tokens or tokens[0][0].startswith(b'#'):
            lines.append(line)
            continue
        words = [token[0].decode() for token in tokens]
        if words == ['loop_']:
            names = []
        elif words[0].startswith('_') and len(words) == 1:
            names.append(words[0])
        elif words[0].startswith('_'):
            names = []
        tags = words[:1] if words[0].startswith('_') and len(words) > 1 else names
        cells = tokens[1:] if tags == words[:1] else tokens
        if not tags or (words[0].startswith('_') and len(words) == 1):
            lines.append(line)
            continue
        assert len(tags) == len(cells), (
            'Saved derived records must retain their declared row shape'
        )
        edits = []
        for tag, token in zip(tags, cells, strict=True):
            word = token[0]
            if b'(' in word or not (tag in DERIVED or tag in DEPENDENTS):
                continue
            try:
                number = float(word)
            except ValueError:
                continue
            assert math.isfinite(number), 'Calculated saved fields must be finite'
            if predicted_values is not None:
                prediction = next(predicted_values, None)
                assert prediction is not None, 'Reopening must not add derived rows'
                wanted_tag, wanted = prediction
                assert tag == wanted_tag, (
                    'Recalculation must retain derived field order and identity'
                )
                assert math.isclose(number, float(wanted), rel_tol=1e-9, abs_tol=1e-11), (
                    'Reopened derived fields must match the native written-model calculation: '
                    + tag
                )
            values.append((tag, word))
            edits.append((token.start(), token.end()))
        for start, end in reversed(edits):
            line = line[:start] + b'<CALCULATED>' + line[end:]
        lines.append(line)
    if predicted_values is not None:
        assert next(predicted_values, None) is None, 'Recalculation must retain every derived row'
    return b''.join(lines), values


def assert_documents(before, after, expected):
    assert before.keys() == after.keys(), 'Reopening must retain every saved file path'
    for name, data in before.items():
        original = data
        current = after[name]
        if name == 'project.edi':
            pattern = rb'(?m)^(_metadata\.last_modified[ \t]+).+$'
            assert len(re.findall(pattern, original)) == len(re.findall(pattern, current)) == 1, (
                'Saved projects require exactly one last-modified field'
            )
            original = re.sub(pattern, rb'\1<WALL-CLOCK>', original)
            current = re.sub(pattern, rb'\1<WALL-CLOCK>', current)
        if name.startswith(('structures/', 'experiments/')) and name.endswith('.edi'):
            skeleton, source_values = projection(original)
            _, expected_values = projection(expected[name])
            actual_skeleton, actual_values = projection(current, expected_values)
            assert skeleton == actual_skeleton, (
                'Reopening preserves all value(s.u.), input, flag, label and non-derived bytes: '
                + name
            )
            assert len(source_values) == len(expected_values) == len(actual_values), (
                'Reopening must retain every calculated field and row'
            )
            for (tag, old), (expected_tag, wanted), (_, actual) in zip(
                source_values, expected_values, actual_values, strict=True
            ):
                assert tag == expected_tag, (
                    'The native calculation must retain derived field identity'
                )
                if tag in DEPENDENTS:
                    assert actual == (old if float(old) == float(wanted) else wanted), (
                        'Bare model values retain fixed bytes or match native symmetry'
                    )
        else:
            assert current == original, (
                'Reopening must preserve the complete fit record and other saved bytes: ' + name
            )


def archive_files(path):
    with zipfile.ZipFile(path) as archive:
        names = [name for name in archive.namelist() if not name.endswith('/')]
        roots = [name[: -len('project.edi')] for name in names if name.endswith('/project.edi')]
        assert len(roots) == 1, 'A saved browser archive must have exactly one project root'
        root = roots[0]
        assert len(set(names)) == len(names), 'Saved archives must not duplicate a file path'
        assert all(name.startswith(root) for name in names), (
            'All saved files must belong to the project'
        )
        return {name[len(root) :]: archive.read(name) for name in names}


def assert_reopened(before_path, after_path):
    before, after = archive_files(before_path), archive_files(after_path)
    with tempfile.TemporaryDirectory(prefix='browser-written-model-') as directory:
        source, destination = Path(directory) / 'source', Path(directory) / 'expected'
        for name, data in before.items():
            target = source / name
            assert target.resolve().is_relative_to(source.resolve()), (
                'Saved project paths must stay under their root'
            )
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        model = edi.Project.load(source)
        model.analysis.calculate()
        model.save_as(destination)
        expected = {
            p.relative_to(destination).as_posix(): p.read_bytes()
            for p in destination.rglob('*')
            if p.is_file()
        }
        assert_documents(before, after, expected)


if __name__ == '__main__':
    assert_reopened(*sys.argv[1:])
