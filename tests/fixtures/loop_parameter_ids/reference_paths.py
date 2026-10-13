"""Read each immutable reference input once and map engine labels to declared row IDs."""

from tests.fixtures.loop_parameter_ids.historical_fit_ids import _loops  # noqa: PLC2701


def reference_paths(project):
    result = {}
    for path in sorted((project / 'experiments').glob('*.edi')):
        loops = list(_loops(path.read_bytes()))
        backgrounds = [
            row for tags, rows in loops if '_background.position' in tags for row in rows
        ]
        links = [
            row for tags, rows in loops if '_linked_structure.structure_id' in tags for row in rows
        ]
        assert len(links) == 1, 'Each frozen scale label must reach exactly one declared structure'
        result[path.stem] = {
            'background': [
                row.get('_background.id', str(i + 1)) for i, row in enumerate(backgrounds)
            ],
            'structure': links[0]['_linked_structure.structure_id'],
        }
    return result
