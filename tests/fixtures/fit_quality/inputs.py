"""Closed-form observation-coverage inputs for the real fit-quality command.

All observations are ten with unit sigma. Only the final included calculation is zero,
so Rwp is 1/sqrt(N), and dropping any required row changes the comparison population.
Profiles are synthetic input, never outputs of a diffraction engine or a FullProf run.
"""

import json

BEGIN = '<!-- fit-quality tables: written by tools/comparison/fit_quality.py -->'
END = '<!-- end of the fit-quality tables -->'


def write(root, relative, text):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def record(root, relative, value):
    write(root, relative, json.dumps(value))


def comparison_case(root, banks, missing, *, excluded=False, rounded=False):
    case = 'pd-neut-tof_coverage_scan' if len(banks) == 1 else 'pd-neut-tof_coverage_joint'
    write(
        root, 'docs/user/cli/projects.yml', f'projects:\n  - id: {case}\n    user-facing: true\n'
    )
    write(root, f'docs/user/cli/{case}/project/project.edi', '_metadata.purpose fitting\n')
    write(root, 'docs/user/guides/fit-quality.md', BEGIN + '\n' + END + '\n')
    comparison = f'knowledge/comparison/{case}'
    reference = f'knowledge/fitting/fullprof/{case}'
    metadata = {'banks': banks, 'n_free': 0, 'cells': {}}
    record(root, f'{comparison}/edi/reference.json', metadata)
    record(
        root, f'{comparison}/diffraction-lib/reference.json', metadata | {'model_compatible': True}
    )
    record(root, f'{reference}/reference.json', metadata)
    write(root, f'{reference}/fit.new', '')
    n_points = 0
    for bank_index, bank in enumerate(banks):
        rows = ['x,observed,calculated,sigma,included']
        fp = ['BEGIN']
        for index, x in enumerate([1.0, 2.0, 3.0, 4.0]):
            included = not (excluded and index == 3 and bank_index == len(banks) - 1)
            calculated = 0 if bank_index == len(banks) - 1 and index == 3 else 10
            measured = x + (0.0004 if rounded else 0)
            rows.append(f'{measured},10,{calculated},1,{int(included)}')
            n_points += included
            if bank_index == len(banks) - 1 and index == missing:
                continue
            fp.append(f'{x:.3f} 10 {calculated} 0')
        for program in ['edi', 'diffraction-lib']:
            write(root, f'{comparison}/{program}/{bank}.csv', '\n'.join(rows) + '\n')
        name = 'fit.prf' if len(banks) == 1 else f'fit_{bank_index + 1}.prf'
        write(root, f'{reference}/{name}', '\n'.join([*fp, 'END']) + '\n')
    return case, n_points


def matching_case(root, layout, scenario):
    """Author exact observation identities, including sparse and rounded profile exports."""
    banks = ['bank'] if layout == 'single' else ['bank-a', 'bank-b']
    target = 0 if layout != 'joint-last' else 1
    case, _ = comparison_case(root, banks, None)
    target_grid = {
        'irregular-middle': [10.0, 10.001, 10.008, 10.02],
        'singleton-far': [10.0],
        'rounded-collision': [10.0001, 10.0002, 10.0011],
        'rounded-complete': [10.0004, 10.0104, 10.0304],
        'singleton-rounded': [10.0004],
        'excluded-claim': [10.0, 10.0001, 10.001],
    }.get(scenario, [10.0, 10.001, 10.002])
    missing = {
        'dense-lower': 0,
        'dense-middle': 1,
        'dense-upper': 2,
        'irregular-middle': 1,
        'excluded-dense-gap': 1,
        'excluded-claim': 1,
    }.get(scenario)
    count = 0
    for bank_index, bank in enumerate(banks):
        grid = target_grid if bank_index == target else [1.0, 2.0, 3.0, 4.0]
        rows, profile = ['x,observed,calculated,sigma,included'], []
        for index, x in enumerate(grid):
            selected = bank_index == target
            calculated = 0 if selected and index == len(grid) - 1 else 10
            included = not (
                selected and scenario in {'excluded-dense-gap', 'excluded-claim'} and index == 1
            )
            rows.append(f'{x},10,{calculated},1,{int(included)}')
            count += included
            if selected and index == missing:
                continue
            profile.append((x, calculated))
            if selected and scenario == 'duplicate-reference' and index == 1:
                profile.append((x, calculated))
        if bank_index == target and scenario == 'singleton-far':
            profile = [(1.0, 10), (2.0, 10)]
        for program in ['edi', 'diffraction-lib']:
            write(
                root, f'knowledge/comparison/{case}/{program}/{bank}.csv', '\n'.join(rows) + '\n'
            )
        name = 'fit.prf' if len(banks) == 1 else f'fit_{bank_index + 1}.prf'
        write(
            root,
            f'knowledge/fitting/fullprof/{case}/{name}',
            'BEGIN\n'
            + ''.join(f'{x:.3f} 10 {calculated} 0\n' for x, calculated in profile)
            + 'END\n',
        )
    return case, count, banks[target]
