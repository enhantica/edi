"""Independent lexical cases: CIF 1.1 kinds and complete numeric declarations."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Case:
    family: str
    tag: str
    source: str
    good: str
    kind: str
    routes: tuple = ('native-project', 'native-factory', 'cif-project', 'cif-factory')
    variant: str = 'selected'

    @property
    def missing_accepts(self):
        return (
            self.family == 'symmetry_form'
            or self.tag == '_parent_space_group.child_transform_Pp_abc'
            or (
                self.family == 'form_factor'
                and (self.kind == 'number' or self.tag.endswith('.approximation'))
            )
        )


BASE = """data_cosio
_edi.schema_version 3
_cell.length_a 4
_cell.length_b 5
_cell.length_c 6
_cell.angle_alpha 90
_cell.angle_beta 90
_cell.angle_gamma 90
_space_group.name_h_m "P 1"
_parent_space_group.name_H-M_alt "P 1"
_parent_space_group.IT_number 1
_parent_space_group.transform_Pp_abc "a,b,c;0,0,0"
_parent_space_group.child_transform_Pp_abc "a,b,c;0,0,0"
_parent_space_group.reference_setting standard
_parent_space_group.derived false
loop_
_atom_site.id
_atom_site.type_symbol
_atom_site.fract_x
_atom_site.fract_y
_atom_site.fract_z
_atom_site.wyckoff_letter
_atom_site.occupancy
_atom_site.adp_iso
_atom_site.adp_type
A Ho 0 0 0 a 1 0 Biso
loop_
_space_group_symop_magn_operation.id
_space_group_symop_magn_operation.xyz
1 x,y,z,+1
loop_
_space_group_symop_magn_centering.id
_space_group_symop_magn_centering.xyz
1 x,y,z,+1
"""


def cases():
    rows = []
    forms = [
        ('crystalaxis', ('x', 'y', 'z'), ('1.5', '0', '0')),
        ('Cartn', ('x', 'y', 'z'), ('1.5', '0', '0')),
        (
            'spherical',
            ('spherical_modulus', 'spherical_polar', 'spherical_azimuthal'),
            ('1.5', '90', '0'),
        ),
    ]
    for form, components, values in forms:
        tags = [
            '_atom_site_moment.' + (part if form == 'spherical' else form + '_' + part)
            for part in components
        ]
        for redundant in (False, True):
            # A malformed redundant form must not be discarded as though it were absent.
            if redundant and form == 'crystalaxis':
                continue
            prefix_tags = (
                ['_atom_site_moment.crystalaxis_' + axis for axis in 'xyz'] if redundant else []
            )
            prefix_values = ['1.5', '0', '0'] if redundant else []
            for i, tag in enumerate(tags):
                cells = prefix_values + list(values)
                cells[len(prefix_values) + i] = '{value}'
                source = (
                    BASE
                    + 'loop_\n_atom_site_moment.label\n'
                    + '\n'.join(prefix_tags + tags)
                    + '\nA '
                    + ' '.join(cells)
                    + '\n'
                )
                rows.append(
                    Case(
                        'moments',
                        tag,
                        source,
                        values[i],
                        'number',
                        routes=('cif-project', 'cif-factory')
                        if form != 'crystalaxis'
                        else ('native-project', 'native-factory', 'cif-project', 'cif-factory'),
                        variant='redundant' if redundant else 'selected',
                    )
                )
    moment = (
        'loop_\n_atom_site_moment.label\n_atom_site_moment.crystalaxis_x\n'
        '_atom_site_moment.crystalaxis_y\n_atom_site_moment.crystalaxis_z\nA 1.5 0 0\n'
    )
    tags = [
        '_magnetic_form_factor.' + item
        for item in [
            'type_symbol',
            'ion',
            'approximation',
            'j2_coefficient',
            'j4_coefficient',
            'j6_coefficient',
        ]
    ]
    for i, tag in enumerate(tags):
        values = ['Ho', 'Ho3+', 'beyond_dipole', '0', '0', '0']
        good = values[i]
        values[i] = '{value}'
        source = BASE + moment + 'loop_\n' + '\n'.join(tags) + '\n' + ' '.join(values) + '\n'
        kind = 'number' if i >= 3 else 'selector' if i in {1, 2} else 'text'
        rows.append(Case('form_factor', tag, source, good, kind))
    for family, category, field, good in [
        ('propagation', 'parent_propagation_vector', 'kxkykz', '0,0,0'),
        ('transforms', 'space_group_magn_transforms', 'Pp_abc', 'a,b,c;0,0,0'),
        ('transforms', 'space_group_magn_transforms', 'source', 'published'),
        ('operations', 'space_group_symop_magn_operation', 'xyz', 'x,y,z,+1'),
        ('centrings', 'space_group_symop_magn_centering', 'xyz', 'x,y,z,+1'),
    ]:
        tag = '_' + category + '.' + field
        if family in {'operations', 'centrings'}:
            source = BASE.replace('1 x,y,z,+1', '1 {value}', 1 if family == 'operations' else 0)
            if family == 'centrings':
                at = BASE.index('_space_group_symop_magn_centering.xyz')
                source = BASE[:at] + BASE[at:].replace('1 x,y,z,+1', '1 {value}')
            source += moment
        elif family == 'transforms':
            values = ['a,b,c;0,0,0', 'published']
            values[0 if field == 'Pp_abc' else 1] = '{value}'
            source = (
                BASE + moment + 'loop_\n_space_group_magn_transforms.id\n'
                '_space_group_magn_transforms.Pp_abc\n_space_group_magn_transforms.source\n'
                + '1 '
                + ' '.join(values)
                + '\n'
            )
        else:
            source = BASE + moment + f'loop_\n_{category}.id\n{tag}\n1 {{value}}\n'
        rows.append(
            Case(
                family,
                tag,
                source,
                good,
                'text' if family == 'transforms' else 'grammar',
            )
        )
    metadata = next(c for c in rows if c.tag == '_space_group_magn_transforms.Pp_abc')
    rows.append(  # noqa: FURB113 — distinct metadata controls
        Case(
            metadata.family,
            metadata.tag,
            metadata.source,
            'not a transform; ? .',
            'text',
            variant='arbitrary-text',
        )
    )
    rows.append(
        Case(
            'description',
            '_space_group_magn.name_BNS',
            BASE + moment + '_space_group_magn.name_BNS {value}\n',
            'P 1',
            'text',
        )
    )
    rows.append(
        Case(
            'symmetry_form',
            '_atom_site_moment.symmform',
            BASE
            + moment.replace(
                '_atom_site_moment.crystalaxis_z\nA 1.5 0 0',
                '_atom_site_moment.crystalaxis_z\n_atom_site_moment.symmform\nA 1.5 0 0 {value}',
            ),
            'Mx,My,Mz',
            'grammar',
        )
    )
    rows.extend(parent_cases(moment))
    rows.extend(mixed_cases(moment))
    rows.extend(metadata_cases(moment))
    for category in ('operation', 'centering'):
        tag = '_space_group_symop_magn_' + category + '.id'
        at = BASE.index(tag)
        source = BASE[:at] + BASE[at:].replace('1 x,y,z,+1', '{value} x,y,z,+1', 1) + moment
        rows.append(Case('keys', tag, source, '1', 'text'))
    rows.append(
        Case(
            'description',
            '_space_group_magn.number_BNS',
            BASE + moment + '_space_group_magn.number_BNS {value}\n',
            '1.1',
            'text',
            ('native-project', 'native-factory'),
            variant='metadata',
        )
    )
    return rows


def mixed_cases(moment):
    both = BASE.replace('A Ho 0 0 0 a 1 0 Biso', 'A Ho 0 0 0 a 1 0 Biso\nB Er .2 .3 .4 a 1 0 Biso')
    both += moment + 'B 0 1.5 0\n'
    header = (
        'loop_\n_magnetic_form_factor.type_symbol\n_magnetic_form_factor.ion\n'
        '_magnetic_form_factor.approximation\n_magnetic_form_factor.j2_coefficient\n'
        '_magnetic_form_factor.j4_coefficient\n_magnetic_form_factor.j6_coefficient\n'
    )
    rows = []
    for index, ion in [(0, 'Ho3+'), (1, 'Er3+')]:
        # Bare cells share both a row and a column with a separately quoted marker.
        values = ['Ho ? beyond_dipole 0 ? 0\n', 'Er ? beyond_dipole 0 ? 0\n']
        values[index] = values[index].replace(' ? beyond', ' {value} beyond')
        rows.append(
            Case(
                'form_factor',
                '_magnetic_form_factor.ion',
                both + header + ''.join(values),
                ion,
                'selector',
                ('native-project', 'native-factory'),
                variant='mixed-first' if index == 0 else 'mixed-last',
            )
        )
    text = BASE + moment + '_space_group_magn.name_UNI ?\n_space_group_magn.name_BNS {value}\n'
    rows.append(
        Case(
            'description', '_space_group_magn.name_BNS', text, 'P 1', 'text', variant='mixed-text'
        )
    )
    return rows


def parent_cases(moment):
    rows = []
    for tag in [
        '_parent_space_group.transform_Pp_abc',
        '_parent_space_group.child_transform_Pp_abc',
    ]:
        source = (BASE + moment).replace(tag + ' "a,b,c;0,0,0"', tag + ' {value}')
        rows.append(
            Case(
                'transforms',
                tag,
                source,
                'a,b,c;0,0,0',
                'grammar' if 'child_transform' in tag else 'text',
            )
        )
    source = (BASE + moment).replace(
        '_parent_space_group.IT_number 1', '_parent_space_group.IT_number {value}'
    )
    rows.append(
        Case(
            'description',
            '_parent_space_group.IT_number',
            source,
            '1',
            'text',
            ('native-project', 'native-factory'),
        )
    )
    source = source.replace('_space_group.name_h_m "P 1"\n', '')
    rows.append(
        Case(
            'description',
            '_parent_space_group.IT_number',
            source,
            '1',
            'number',
            ('cif-project', 'cif-factory'),
        )
    )
    source = (BASE + moment).replace('_space_group.name_h_m "P 1"\n', '')
    source = source.replace('_parent_space_group.IT_number 1\n', '')
    source += '_space_group_magn.number_BNS {value}\n'
    rows.append(
        Case(
            'description',
            '_space_group_magn.number_BNS',
            source,
            '1.1',
            'grammar',
            ('cif-project', 'cif-factory'),
            variant='derived-family',
        )
    )
    return rows


def cif(source):
    source = source.replace('_edi.schema_version 3\n', '')
    source = source.replace('_space_group.name_h_m', '_space_group_name_H-M_alt')
    source = source.replace('_atom_site.id', '_atom_site_label')
    source = source.replace('_atom_site.adp_iso', '_atom_site_B_iso_or_equiv')
    source = source.replace('_atom_site.wyckoff_letter', '_atom_site_Wyckoff_symbol')
    for category in ('cell', 'atom_site'):
        source = source.replace('_' + category + '.', '_' + category + '_')
    source = source.replace('_magnetic_form_factor.', '_edi_magnetic_form_factor.')
    return source.replace('_parent_space_group.derived', '_edi_parent_space_group.derived')


GRAMMAR_BAD = {
    'description': ('1.5abc', '1junk', '1.1junk', '1.', '.1'),
    'operations': (
        'x+0junk,y,z,+1',
        'x,y+0junk,z,+1',
        'x,y,z+0junk,+1',
        'x+1/2*x,y,z,+1',
        'x,y,z,+1,',
        'x,y,z,+1,0',
        'x,y,z,+1,,',
        'x+1/0,y,z,+1',
    ),
    'centrings': (
        'x+0junk,y,z,+1',
        'x,y+0junk,z,+1',
        'x,y,z+0junk,+1',
        'x+1/2*x,y,z,+1',
        'x,y,z,+1,',
        'x,y,z,+1,0',
        'x,y,z,+1,,',
        'x+1/0,y,z,+1',
    ),
    'propagation': (
        '0junk,0,0',
        '0,0junk,0',
        '0/1junk,0,0',
        '0,0',
        '0,0,0,',
        '0,0,0,1junk',
        '1/0,0,0',
        '1e308/1e-308,0,0',
    ),
    'symmetry_form': (
        'Mx/0,My,Mz',
        '1e308/0.00000000000000000001Mx,My,Mz',
        '1e308Mx/0.00000000000000000001,My,Mz',
        '1/0Mx,My,Mz',
        '1e308/1e-308Mx,My,Mz',
        'Mx,My,Mz,',
        'Mx,My',
        'Mx,My,Mz,0',
        'Mx+1junk,My,Mz',
    ),
    'transforms': (
        'a,b;0,0,0',
        'a,b,c,;0,0,0',
        'a,b,c;0,0',
        'a,b,c;0,0,0,',
        'a,b,c;0,0,0,1junk',
        'a,b,c;1/0,0,0',
        'a,b,c;1e308/1e-308,0,0',
        '1junka,b,c;0,0,0',
        'a,1junkb,c;0,0,0',
        'a,b,1junkc;0,0,0',
        'a,b,c;0junk,0,0',
        'a,b,c;0,0junk,0',
        'a,b,c;0,0,0junk',
    ),
}


def tokens(case):
    yield 'valid', '"' + case.good + '"' if ' ' in case.good else case.good
    if case.kind == 'number':
        for suffix in ('abc', '(2)abc', 'e+', '(2x)'):
            yield 'invalid', case.good + suffix
        for nonfinite in ('nan', 'inf', '-inf', '1e999'):
            yield 'invalid', nonfinite
    elif case.kind == 'grammar':
        yield 'invalid', case.good + 'junk'
        yield from (('invalid', bad) for bad in dict.fromkeys(GRAMMAR_BAD.get(case.family, ())))
    elif case.kind == 'selector':
        yield 'invalid', '1.5abc'
    for marker in ('?', '.'):
        yield 'missing', marker
        yield 'literal', "'" + marker + "'"
        yield 'literal', '"' + marker + '"'


def metadata_cases(moment):
    rows = []
    for field, good in [
        ('name_UNI', 'P 1'),
        ('name_OG', 'P 1'),
        ('number_OG', '1.1.1'),
        ('point_group_name_UNI', '1'),
        ('point_group_number_Litvin', '1'),
    ]:
        tag = '_space_group_magn.' + field
        rows.append(Case('description', tag, BASE + moment + tag + ' {value}\n', good, 'text'))
    for field, good in [
        ('name_H-M_alt', 'P 1'),
        ('reference_setting', 'standard'),
        ('derived', 'false'),
    ]:
        tag = '_parent_space_group.' + field
        source = BASE + moment
        if field == 'name_H-M_alt':
            source = source.replace(tag + ' "P 1"', tag + ' {value}')
        else:
            source = source.replace(tag + ' ' + good, tag + ' {value}')
        rows.append(
            Case('description', tag, source, good, 'selector' if field == 'derived' else 'text')
        )
    for tag, source in [
        ('_atom_site_moment.label', (BASE + moment).replace('\nA 1.5 0 0', '\n{value} 1.5 0 0')),
        (
            '_parent_propagation_vector.id',
            BASE
            + moment
            + 'loop_\n_parent_propagation_vector.id\n_parent_propagation_vector.kxkykz\n{value} 0,0,0\n',  # noqa: E501 — explicit lexical cases and consumer obligations
        ),
        (
            '_space_group_magn_transforms.id',
            BASE
            + moment
            + 'loop_\n_space_group_magn_transforms.id\n_space_group_magn_transforms.Pp_abc\n{value} a,b,c;0,0,0\n',  # noqa: E501 — explicit lexical cases and consumer obligations
        ),
    ]:
        rows.append(
            Case(
                'keys',
                tag,
                source,
                'A' if 'label' in tag else '1',
                'selector' if 'label' in tag else 'text',
            )
        )
    return rows


GRAMMAR_BAD['operations'] += ('x,y,z,+1,', 'x,y,z,+1,0', 'x,y,z,+1,,', 'x+1/0,y,z,+1')
GRAMMAR_BAD['centrings'] += ('x,y,z,+1,', 'x,y,z,+1,0', 'x,y,z,+1,,', 'x+1/0,y,z,+1')


def partial_moment_declarations(form):
    """A declared converted form has three columns, even beside another form."""
    for variant in ('selected', 'redundant'):
        case = next(
            c for c in cases() if c.family == 'moments' and form in c.tag and c.variant == variant
        )
        complete = case.source.format(value=case.good)
        yield 'valid', complete, case.tag
        for tag in [
            line for line in complete.splitlines() if line.startswith('_atom_site_moment.' + form)
        ]:
            lines = complete.splitlines()
            loop = max(i for i, line in enumerate(lines) if line == 'loop_')
            headers = [line for line in lines[loop + 1 :] if line.startswith('_')]
            index = headers.index(tag)
            cells = lines[-1].split()
            del cells[index]
            lines.remove(tag)
            lines[-1] = ' '.join(cells)
            yield 'invalid', '\n'.join(lines) + '\n', tag


# Only the interpreted child transform uses these malformed compound probes.
GRAMMAR_BAD['transforms'] += ("';0,0,0'", "';1/4,0,0'")
