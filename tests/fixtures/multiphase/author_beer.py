"""Execute the pinned BEER tutorial once; tests consume its committed record."""

import argparse
import ast
import hashlib
import importlib.metadata
import json
import shutil
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def files(home):
    return {str(p.relative_to(home)): digest(p) for p in sorted(home.rglob('*')) if p.is_file()}


def snapshot(project):
    from easydiffraction.analysis.fit_helpers.metrics import (  # noqa: PLC0415
        calculate_weighted_r_factor,
        get_reliability_inputs,
    )

    result = project.analysis.fit_results
    observed, calculated, errors = get_reliability_inputs(
        project.structures, list(project.experiments.values())
    )
    return {
        'success': bool(result.success),
        'message': result.message,
        'iterations': result.iterations,
        'chi_square': result.chi_square,
        'reduced_chi_square': result.reduced_chi_square,
        'rwp': float(calculate_weighted_r_factor(observed, calculated, errors)),
        'minimizer': result.minimizer_type,
        'calculators': {e.name: e.calculator.type.value for e in project.experiments.values()},
        'parameters': {
            p.unique_name: {'value': float(p.value), 'su': p.uncertainty}
            for p in result.parameters
            if hasattr(p, 'uncertainty') and (p.free or p.uncertainty is not None)
        },
        'all_parameters': {
            p.unique_name: {
                'value': p.value,
                'su': getattr(p, 'uncertainty', None),
                'free': getattr(p, 'free', False),
            }
            for p in project.parameters
        },
    }


def validate_unconstrained(project, removed_constraints, expected_constraints):
    if set(removed_constraints) != expected_constraints:
        message = 'The unconstrained capture must omit both known constraints'
        raise ValueError(message)
    if len(project.analysis.constraints) != 0:
        message = 'The unconstrained reference must contain no active constraints'
        raise ValueError(message)
    if len(project.free_parameters) != 56:
        message = 'BEER must retain the tutorial free set and both N2 scales'
        raise ValueError(message)


def write_reference(args, stages, removed_constraints):
    record = {
        'diffraction_lib_commit': '0d9f10e412a0cd08d4dd0af95845dd9bb597dcdf',
        'versions': {
            name: importlib.metadata.version(name)
            for name in ('easydiffraction', 'cryspy', 'numpy', 'scipy', 'lmfit')
        },
        'tutorial_sha256': digest(args.tutorial),
        'archive_sha256': digest(args.archive),
        'initial_sha256': files(args.output / 'initial'),
        'output_sha256': files(args.output / 'stage-2'),
        'stages': stages,
        'reference_variant': (
            'unconstrained-independent-bank-scales'
            if args.without_scale_constraints
            else 'tutorial-cross-bank-constraints'
        ),
        'removed_constraints': removed_constraints,
    }
    (args.output / 'reference.json').write_text(json.dumps(record, indent=2) + '\n')
    print('BEER independent reference complete', flush=True)


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tutorial', required=True, type=Path)
    parser.add_argument('--archive', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--resume-first-stage', type=Path)
    parser.add_argument('--without-scale-constraints', action='store_true')
    return parser.parse_args()


def main():
    args = arguments()
    args.output.mkdir(parents=True, exist_ok=bool(args.resume_first_stage))
    namespace = {'__name__': '__main__', '__file__': str(args.tutorial)}
    stages = []
    resuming = bool(args.resume_first_stage)
    removed_constraints = []
    expected_constraints = {
        'n2_ferrite_scale = s2_ferrite_scale',
        'n2_austenite_scale = s2_austenite_scale',
    }
    for node in ast.parse(args.tutorial.read_text()).body:
        spelling = ast.unparse(node)
        if resuming:
            if spelling != 'project.analysis.fit()':
                continue
            from easydiffraction import Project  # noqa: PLC0415

            project = Project.load(str(args.resume_first_stage))
            namespace.update(
                project=project,
                ferrite=project.structures['ferrite'],
                austenite=project.structures['austenite'],
                expt_s2=project.experiments['expt_s2'],
                expt_n2=project.experiments['expt_n2'],
            )
            stages.append(snapshot(project))
            shutil.copytree(args.resume_first_stage, args.output / 'stage-1')
            (args.output / 'stages.json').write_text(json.dumps(stages, indent=2) + '\n')
            print(
                'BEER tutorial fit 1 captured from its saved checkpoint; no repeat fit', flush=True
            )
            resuming = False
            continue
        # Reuse the verified download; keep extraction and every physics/fit statement.
        if spelling.startswith('zip_path = download_data('):
            namespace['zip_path'] = str(args.archive.resolve())
            continue
        # Rendering has no model effect and needs no browser in an authoring service.
        if isinstance(node, ast.Expr) and spelling.startswith('project.display.'):
            continue
        if args.without_scale_constraints and spelling.startswith(
            'project.analysis.constraints.create('
        ):
            expression = next(
                keyword.value.value
                for keyword in node.value.keywords
                if keyword.arg == 'expression'
            )
            if expression not in expected_constraints or expression in removed_constraints:
                raise ValueError('Only the two declared BEER scale constraints may be omitted')
            removed_constraints.append(expression)
            continue
        is_fit = spelling == 'project.analysis.fit()'
        if is_fit and not stages:
            project = namespace['project']
            if args.without_scale_constraints:
                validate_unconstrained(project, removed_constraints, expected_constraints)
            project.save()
            shutil.copytree(project.metadata.path, args.output / 'initial')
            print('BEER initial project captured; starting tutorial fit 1', flush=True)
        exec(  # noqa: S102
            compile(ast.Module(body=[node], type_ignores=[]), str(args.tutorial), 'exec'),
            namespace,
        )
        if is_fit:
            project = namespace['project']
            stages.append(snapshot(project))
            shutil.copytree(project.metadata.path, args.output / f'stage-{len(stages)}')
            (args.output / 'stages.json').write_text(json.dumps(stages, indent=2) + '\n')
            print(f'BEER tutorial fit {len(stages)} captured', flush=True)
    write_reference(args, stages, removed_constraints)


if __name__ == '__main__':
    main()
