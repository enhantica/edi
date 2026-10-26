"""Independent saved-axis/background forms and fresh-calculation round-trip invariants.

The profile kernel is not a new absolute physics oracle: a fresh calculation from
written rounded inputs is a round-trip invariant independent of the save/adoption
path. Numeric spelling uses Decimal; axes, masks, backgrounds and reflection
metrics use closed forms over the actual written model, never a new byte pin.
"""

from decimal import Decimal, localcontext
from pathlib import Path

import gemmi
import numpy as np

from tests.fixtures.excluded_display.historical_bytes import check_d
from tests.fixtures.project_save.reference import six_digits


def require(condition, message):
    if not condition:
        raise ValueError(message)


def number(text):
    return float(text.split('(')[0])


def rows(block, category):
    table = block.find_mmcif_category(category + '.')
    return [dict(zip(table.tags, list(row), strict=True)) for row in table]


def close_saved(token, expected, message):
    require(
        float(token).hex() == six_digits(float(expected)).hex(),
        f'{message}: wrote {token}; reference {expected:.17g}; '
        f'saved {six_digits(float(expected))}',
    )


def metric(block):
    lengths = [Decimal(block.find_value('_cell.length_' + key).split('(')[0]) for key in 'abc']
    angles = [number(block.find_value('_cell.angle_' + key)) for key in ('alpha', 'beta', 'gamma')]
    require(
        all(angle.hex() == (90.0).hex() for angle in angles),
        'The carried-result witnesses declare independently orthogonal cell metrics',
    )
    return lengths


def reciprocal_spacing(lengths, indices):
    # Decimal keeps exact half-way d values (e.g. 5.431/16) on their correct side
    # of the six-digit boundary instead of adding binary matrix-inversion noise.
    with localcontext() as context:
        context.prec = 50
        return sum(
            (Decimal(index) / length) ** 2 for index, length in zip(indices, lengths, strict=True)
        ).sqrt()


def check(directory, engine):  # noqa: PLR0914 - each physical column has its own operand
    root = Path(directory)
    fresh = engine.Project.load(root)
    fresh.analysis.calculate()
    metrics = {
        path.stem: metric(gemmi.cif.read_file(str(path)).sole_block())
        for path in (root / 'structures').glob('*.edi')
    }
    evidence = {}
    for path in sorted((root / 'experiments').glob('*.edi')):
        block = gemmi.cif.read_file(str(path)).sole_block()
        data, reflections = rows(block, '_data'), rows(block, '_refln')
        require(
            bool(data) and bool(reflections), 'Carried results must write data and reflection rows'
        )
        observed = fresh.experiments[path.stem]
        scalar = {
            key.encode(): block.find_value(key).encode()
            for key in (
                '_instrument.setup_wavelength',
                '_instrument.calib_d_to_tof_offset',
                '_instrument.calib_d_to_tof_linear',
                '_instrument.calib_d_to_tof_quadratic',
                '_instrument.calib_d_to_tof_reciprocal',
            )
            if block.find_value(key)
        }
        axis = 'two_theta' if '_data.two_theta' in data[0] else 'time_of_flight'
        exclusions = rows(block, '_excluded_region')
        anchors = rows(block, '_background')
        require(
            block.find_value('_background.type') == 'line-segment',
            'Carried-result background witnesses declare the independently interpolated basis',
        )
        x_anchor = [number(row['_background.position']) for row in anchors]
        y_anchor = [number(row['_background.intensity']) for row in anchors]
        require(bool(anchors), 'The independent background comparison reaches authored anchors')
        arrays = {
            key: np.array(getattr(observed.data, key), copy=True)
            for key in ('intensity_calc', 'intensity_bkg', 'calc_status')
        }
        require(
            all(len(values) == len(data) for values in arrays.values()),
            'Saved and freshly calculated data retain exactly the same row population',
        )
        for index, row in enumerate(data):
            check_d(
                {key.encode(): value.encode() for key, value in row.items()},
                scalar,
                saved_precision=True,
            )
            x = number(row['_data.' + axis])
            excluded = any(
                min(
                    number(region['_excluded_region.start']),
                    number(region['_excluded_region.end']),
                )
                <= x
                <= max(
                    number(region['_excluded_region.start']),
                    number(region['_excluded_region.end']),
                )
                for region in exclusions
            )
            require(
                row['_data.calc_status'] == ('excl' if excluded else 'incl'),
                'Every saved calc status follows independent closed-interval exclusions',
            )
            for key in ('intensity_calc', 'intensity_bkg'):
                token = row['_data.' + key]
                if excluded:
                    require(
                        token.strip() == '.',
                        'Excluded calculated columns remain inapplicable dots',
                    )
                else:
                    close_saved(
                        token,
                        arrays[key][index],
                        'Every saved intensity follows independent Decimal spelling of a '
                        'fresh calculation from the written rounded model',
                    )
            if not excluded:
                close_saved(
                    row['_data.intensity_bkg'],
                    np.interp(x, x_anchor, y_anchor),
                    'Every included background follows independent linear interpolation',
                )
        fresh_reflections = observed.refln
        require(
            len(fresh_reflections.index_h) == len(reflections),
            'A fresh rounded-model calculation retains every saved reflection row',
        )
        for index, row in enumerate(reflections):
            require(
                row['_refln.id'] == str(index + 1),
                'Written reflection IDs retain their independent positional order',
            )
            require(
                row['_refln.structure_id'] in metrics,
                'Every written reflection refers to an actual written structure',
            )
            hkl = [int(row['_refln.index_' + key]) for key in 'hkl']
            inverse_d = reciprocal_spacing(metrics[row['_refln.structure_id']], hkl)
            close_saved(
                row['_refln.d_spacing'],
                1 / inverse_d,
                'Reflection d follows the independently inverted written cell metric',
            )
            close_saved(
                row['_refln.sin_theta_over_lambda'],
                inverse_d / 2,
                'Reflection scattering coordinates follow the independent reciprocal metric',
            )
            for key in ('index_h', 'index_k', 'index_l', 'structure_id'):
                require(
                    str(getattr(fresh_reflections, key)[index]) == row['_refln.' + key],
                    'Fresh calculation preserves every saved reflection identity and order',
                )
            for key in ('f_calc', 'f_squared_calc', axis):
                close_saved(
                    row['_refln.' + key],
                    getattr(fresh_reflections, key)[index],
                    'Every saved reflection value follows independent Decimal spelling '
                    'of a fresh calculation from written inputs',
                )
        evidence[path.name] = {
            'data_rows': len(data),
            'reflection_rows': len(reflections),
            'data_columns': sorted(data[0]),
            'reflection_columns': sorted(reflections[0]),
        }
    return evidence


def check_escapes(directory, engine):
    """Exercise every computed field on one declared project, restoring exact bytes."""
    path = next((Path(directory) / 'experiments').glob('*.edi'))
    original = path.read_bytes()
    witnessed = []
    for category in ('_data', '_refln'):
        document = gemmi.cif.read_string(original.decode())
        table = document.sole_block().find_mmcif_category(category + '.')
        tags = [
            tag
            for tag in table.tags
            if category == '_refln'
            or tag.split('.')[1] in {'d_spacing', 'intensity_calc', 'intensity_bkg', 'calc_status'}
        ]
        for tag in tags:
            document = gemmi.cif.read_string(original.decode())
            table = document.sole_block().find_mmcif_category(category + '.')
            selected = next(row for row in table if row[tag] != '.')
            old = selected[tag]
            if tag.endswith('.calc_status'):
                selected[tag] = 'excl' if old == 'incl' else 'incl'
            elif tag.endswith('.structure_id'):
                selected[tag] = old + '_wrong'
            elif tag.rsplit('.', 1)[1] in {'id', 'index_h', 'index_k', 'index_l'}:
                selected[tag] = str(int(old) + 1)
            else:
                selected[tag] = format(number(old) * 1.03125 + 0.125, '.17g')
            path.write_text(document.as_string())
            try:
                try:
                    check(directory, engine)
                except ValueError:
                    witnessed.append(tag)
                else:
                    message = 'An altered computed column must refuse: ' + tag
                    raise AssertionError(message)
            finally:
                path.write_bytes(original)
    return witnessed
