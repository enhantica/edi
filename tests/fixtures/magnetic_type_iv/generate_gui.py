"""Build invented public inputs for the native magnetic workflows."""

from pathlib import Path

ROOT = Path(__file__).parent


def parent(group='P n m a', name='parent', gamma=90):
    return f'''data_{name}
_edi.schema_version 3
_cell.length_a 6
_cell.length_b 7
_cell.length_c 8
_cell.angle_alpha 90
_cell.angle_beta 90
_cell.angle_gamma {gamma}
_space_group.name_h_m "{group}"
loop_
_atom_site.id
_atom_site.type_symbol
_atom_site.wyckoff_letter
_atom_site.fract_x
_atom_site.fract_y
_atom_site.fract_z
_atom_site.occupancy
_atom_site.adp_iso
_atom_site.adp_type
Co1 Co . .13 .25 .31 1 .17 Biso
'''


def main():
    source = ROOT.parent / 'adp_site_symmetry/gui/cubic'
    for name in [
        'popup',
        'unlinked',
        'overflow',
        'type-iv',
        'unverified',
        'f-cubic',
        'a-setting',
        'mixed-enabled',
        'mixed-disabled',
    ]:
        root = ROOT / 'gui' / name
        (root / 'structures').mkdir(parents=True, exist_ok=True)
        (root / 'project.edi').write_text('_edi.schema_version 3\n_metadata.name magnetic_test\n')
        text = parent()
        if name in {'type-iv', 'unverified'}:
            text = (ROOT / 'pnma-d.edi').read_text().replace('data_type_iv', 'data_parent')
            if name == 'unverified':
                text = text.replace('62.452', '62.441')
        if name == 'f-cubic':
            text = (
                parent('F m -3 m')
                .replace('_cell.length_b 7', '_cell.length_b 6')
                .replace('_cell.length_c 8', '_cell.length_c 6')
            )
        if name == 'a-setting':
            text = parent('A m m a')
        (root / 'structures/parent.edi').write_text(text)
        if name == 'unlinked':
            continue
        (root / 'experiments').mkdir(exist_ok=True)
        if name in {'popup', 'overflow'}:
            (root / 'structures/unrelated.edi').write_text(parent('P 1', 'unrelated'))
        bank = (source / 'experiments/bank.edi').read_text().replace('structure 1', 'parent 3.6')
        for filename, scale, enabled in [('first', 3.6, 'true'), ('second', 8.4, 'false')]:
            contents = bank.replace('data_bank', 'data_' + filename).replace(
                '_linked_structure.scale\nparent 3.6',
                f'_linked_structure.scale\n_linked_structure.enabled\nparent {scale} {enabled}',
            )
            if name in {'popup', 'overflow'}:
                contents = contents.replace(
                    f'parent {scale} {enabled}\n', f'parent {scale} {enabled}\nunrelated .9 true\n'
                )
                axis = '501 1 0' if name == 'overflow' else '1 1 0'
                contents += f"""loop_
_preferred_orientation.structure_id
_preferred_orientation.march_r
_preferred_orientation.march_random_fract
_preferred_orientation.index_h
_preferred_orientation.index_k
_preferred_orientation.index_l
parent 0.7() 0.13() {axis}
"""
            (root / 'experiments' / (filename + '.edi')).write_text(contents)
        if name.startswith('mixed-'):
            single = (
                ROOT.parent / 'independent_experiments/project/experiments/amber.edi'
            ).read_text()
            single = single.replace(
                'phase_z 0.8', 'parent 0.8 ' + ('true' if name.endswith('enabled') else 'false')
            )
            single = single.replace(
                '_linked_structure.scale\n', '_linked_structure.scale\n_linked_structure.enabled\n'
            )
            (root / 'experiments/single.edi').write_text(single)


if __name__ == '__main__':
    main()
