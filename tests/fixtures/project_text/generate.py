"""Hand-edited text and a classic ZIP boundary, independent of the app writer."""

import argparse
import shutil
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def project(destination):
    destination = Path(destination)
    for relative in ('project.edi', 'structures/structure.edi', 'experiments/experiment.edi'):
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / 'tests/fixtures/table_display' / relative, target)
    original = destination / 'structures/structure.edi'
    (original.parent / 'zz_second.edi').write_text(
        original
        .read_text()
        .replace('data_structure', 'data_zz_second')
        .replace('4.026700', '5.137900')
    )
    analysis = destination / 'analysis/analysis.edi'
    analysis.parent.mkdir(parents=True, exist_ok=True)
    analysis.write_text(
        '_edi.schema_version 3\n_fitting_mode.type single\n_minimizer.type crysta\n'
        'loop_\n_alias.id\n_alias.parameter_unique_name\n'
        'li structure.atom_site.Li1.adp_iso\nf structure.atom_site.F1.adp_iso\n'
        'loop_\n_constraint.id\n_constraint.expression\nf "f = 1.5 * li"\n'
    )
    report = destination / 'reports/report.edi'
    report.parent.mkdir(exist_ok=True)
    report.write_text('_edi.schema_version 3\n_report.html true\n_report.pdf false\n')
    return destination


def invalid_texts(text):
    lines = text.splitlines()
    atom_row = next(index for index, line in enumerate(lines) if line.startswith('Li1 '))
    short = lines.copy()
    short[atom_row] = ' '.join(short[atom_row].split()[:-1])
    return {
        'unknown-item': text + '\n_cell.unknown_length 3.5\n',
        'unknown-category': text + '\n_unknown_category.setting 3.5\n',
        'bad-number': text.replace('_cell.length_a 4.026700', '_cell.length_a not_a_number'),
        'short-loop-row': '\n'.join(short) + '\n',
        'broken-block-name': text.replace('data_structure', 'data_'),
    }


def classic_zip(destination, source, count=65535):
    source = Path(source)
    files = sorted(path for path in source.rglob('*') if path.is_file())
    with zipfile.ZipFile(destination, 'w', allowZip64=False) as archive:
        for path in files:
            archive.writestr(path.relative_to(source).as_posix(), path.read_bytes())
        for index in range(count - len(files)):
            archive.writestr(f'attachments/{index:05d}.txt', b'x')
    return Path(destination)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    source = project(args.destination / 'project')
    classic_zip(args.destination / 'classic-limit.zip', source)
    for name, text in invalid_texts((source / 'structures/structure.edi').read_text()).items():
        (args.destination / (name + '.edi')).write_text(text)


if __name__ == '__main__':
    main()
