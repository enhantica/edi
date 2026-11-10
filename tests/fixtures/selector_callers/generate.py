"""Prepare the committed cobalt structure for selector-only UI witnesses."""

from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / 'magnetic_pnma/app-project/structures/cosio.edi'


def main():
    project = HERE / 'project'
    (project / 'structures').mkdir(parents=True, exist_ok=True)
    (project / 'project.edi').write_text(
        '_edi.schema_version 3\n_metadata.name "Magnetic selector witnesses"\n'
        '_structure_view.show_moments true\n'
    )
    (project / 'structures/cosio.edi').write_bytes(SOURCE.read_bytes())


if __name__ == '__main__':
    main()
