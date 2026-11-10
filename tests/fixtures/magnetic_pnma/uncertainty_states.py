"""Literal states whose expected uncertainties follow hand relation Jacobians.

Orthogonal |(x,0,z)| has gradient (x/r,0,z/r). At x=z=1, sx=.2,
sz=.3 and rho=.5 its variance is .095. With gamma=120 and Mx=My=t,
|M|=|t|, so sigma(|M|)=sigma(t). No fit output supplies an expectation.
"""

from tests.fixtures.magnetic_pnma import commensurate, reference

STATES = (
    'fixed',
    'undefined',
    'missing-pair',
    'correlated',
    'unrelated-undefined',
    'tied',
    'undefined-tied',
    'chain',
    'cross-undefined',
    'constant',
    'symmetry-tied',
    'cell-chain',
    'cell-chain-undefined',
)


def texts(kind):  # noqa: PLR0915 — literal independent uncertainty states
    moment = '1.00(20) 0 1'
    seeds = ['A.crystalaxis_x']
    aliases, expressions, pairs = [], [], []
    extra_atom = extra_moment = ''
    tied = kind in {'tied', 'undefined-tied', 'chain', 'symmetry-tied'}
    if kind in {'undefined', 'missing-pair', 'correlated', 'unrelated-undefined'}:
        moment = '1.00(20) 0 ' + ('1()' if kind == 'undefined' else '1.00(30)')
        seeds.append('A.crystalaxis_z')
    if kind in {'correlated', 'unrelated-undefined'}:
        pairs.append(('A.crystalaxis_x', 'A.crystalaxis_z', '.5'))
    if kind in {'unrelated-undefined', 'chain', 'cross-undefined', 'constant'}:
        extra_atom = 'B Co a .19 .27 .31 1 .17 Biso\n'
        extra_moment = 'B ' + ('.5 0 0' if kind == 'chain' else '.5() 0 0') + '\n'
        if kind != 'chain':
            seeds.append('B.crystalaxis_x')
    if tied:
        moment = ('1()' if kind == 'undefined-tied' else '1.00(20)') + ' 1 0'
        aliases = [('x', 'A.crystalaxis_x'), ('y', 'A.crystalaxis_y')]
        expressions = ['y = x']
    if kind == 'chain':
        aliases.append(('b', 'B.crystalaxis_x'))
        expressions = ['b = .5*x', 'y = 2*b']
    if kind in {'cross-undefined', 'constant'}:
        moment = '1.00(20) 1 0'
        aliases = [('y', 'A.crystalaxis_y'), ('b', 'B.crystalaxis_x')]
        expressions = ['y = ' + ('2*b' if kind == 'cross-undefined' else '0*b + 1')]
    if kind.startswith('cell-chain'):
        moment = ('1()' if kind.endswith('undefined') else '1.00(20)') + ' 0 1'
        aliases = [('x', 'A.crystalaxis_x'), ('b', 'cell.angle_beta')]
        expressions = ['b = 90 + 10*(x - 1)']
    operations = ('x,y,z,+1',)
    if kind == 'symmetry-tied':
        moment = '1.00(20) 1.00(20) 0'
        operations = ('x,y,z,+1', 'y,x,-z,+1')
        seeds = ['A.crystalaxis_y']
        aliases, expressions = [], []
    source = commensurate.structure(
        b=4 if tied else 5, gamma=120 if tied else 90, operations=operations, moment=moment
    )
    if kind == 'symmetry-tied':
        source = source.replace(
            '_parent_space_group.derived false', '_parent_space_group.derived true'
        )
    source = source.replace('A Co a 0 0 0 1 .17 Biso\n', 'A Co a 0 0 0 1 .17 Biso\n' + extra_atom)
    source += extra_moment
    analysis = """_edi.schema_version 3
_fit_result.result_kind deterministic
_fit_result.success true
_fit_result.message done
_fit_result.iterations 1
_fit_result.fitting_time 0
_fit_result.reduced_chi_square 1
_fit_result.objective_name chi_square
_fit_result.objective_value 4
_fit_result.n_data_points 8
_fit_result.n_parameters {count}
_fit_result.n_free_parameters {count}
_fit_result.degrees_of_freedom {dof}
_fit_result.covariance_available true
_fit_result.exit_reason done
_fit_result.profile_function cwl-tch-pseudo-voigt
_fit_result.background_function line-segment
_fit_result.descent ladder
loop_
_fit_parameter.id
_fit_parameter.start_value
_fit_parameter.start_uncertainty
_fit_parameter.start_tied
""".format(count=len(seeds), dof=8 - len(seeds))
    analysis += ''.join('structure.' + name + ' 1 . .\n' for name in seeds)
    if pairs:
        analysis += (
            'loop_\n_fit_parameter_correlation.id\n_fit_parameter_correlation.source_kind\n'
            '_fit_parameter_correlation.parameter_unique_name_i\n'
            '_fit_parameter_correlation.parameter_unique_name_j\n'
            '_fit_parameter_correlation.correlation\n'
        )
        analysis += ''.join(
            f'{i} deterministic cosio.atom_site_moment.{a} cosio.atom_site_moment.{b} {rho}\n'
            for i, (a, b, rho) in enumerate(pairs, 1)
        )
    if aliases:
        analysis += 'loop_\n_alias.id\n_alias.parameter_unique_name\n'
        analysis += ''.join(
            f'{name} cosio.'
            + (target if target.startswith('cell.') else 'atom_site_moment.' + target)
            + '\n'
            for name, target in aliases
        )
        analysis += 'loop_\n_constraint.expression\n'
        analysis += ''.join('"' + expression + '"\n' for expression in expressions)
    analysis += (
        'loop_\n_fit_result_bank.experiment_id\n_fit_result_bank.n_data_points\n'
        '_fit_result_bank.prof_wr_factor\nd20 8 .1\n'
    )
    return source, analysis


def project(root, kind):
    source, analysis = texts(kind)
    reference.project(root, source)
    (root / 'analysis').mkdir()
    (root / 'analysis/analysis.edi').write_text(analysis)
    return root
