"""Build interoperable ZIP inputs with Python's standard archive writer."""

from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[3]
CASES = (
    'sc-neut-tof_taurine_fit',
    'pd-neut-cwl_cosio-d20_scan-3f',
    'sc-neut-cwl_tb2ti2o7-heidi_basic',
)


def put(archive, name, body):
    info = ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = ZIP_DEFLATED
    archive.writestr(info, body)


def main():
    for case in CASES:
        source = ROOT / 'docs/user/cli' / case / 'project'
        with ZipFile(Path(__file__).parent / (case + '.zip'), 'w', ZIP_DEFLATED) as archive:
            for path in sorted(source.rglob('*')):
                if path.is_file():
                    put(archive, path.relative_to(source).as_posix(), path.read_bytes())
            put(archive, 'reports/opaque.html', b'<p>Independently authored report</p>\n')
    with ZipFile(Path(__file__).parent / 'escape.zip', 'w', ZIP_DEFLATED) as archive:
        put(archive, 'project.edi', '_edi.schema_version 3\n_metadata.name hostile\n')
        put(archive, '../escaped.edi', 'outside project\n')


if __name__ == '__main__':
    main()
