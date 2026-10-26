"""Generate opaque archive inputs independently of either ZIP implementation."""

from pathlib import Path

FILES = {
    'project.edi': b'_edi.schema_version 4\n_metadata.name "Archive permissions"\n',
    'structures/phase.edi': b'data_phase\n_cell.length_a 3.890915\n',
    'notes/r\u00e9sum\u00e9.txt': b'Readable after extraction: \xce\xb1\n',
    'empty.dat': b'',
    '.hidden': bytes([0, 255, 16, 127]),
}


def main():
    root = Path(__file__).resolve().parent / 'project'
    for name, data in FILES.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)


if __name__ == '__main__':
    main()
