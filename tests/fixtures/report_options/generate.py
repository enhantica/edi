"""Declare the independent pair-strength and clique fixtures for correlation ties."""

import argparse
import itertools
import json
import re
import shutil
from pathlib import Path


def generate(repo, target):
    target.mkdir(parents=True, exist_ok=True)
    graphs = {
        'pairs': {
            'names': ['P1', 'P2', 'P3', 'P4', 'P5', 'P6'],
            'default': 0.1,
            'pairs': {'P1,P2': 0.99, 'P3,P4': 0.95, 'P5,P6': 0.9},
        },
        'nontrivial': {
            'names': ['A', 'B', 'C', 'D', 'E', 'F'],
            'default': 0.1,
            'pairs': {'A,B': 0.99, 'A,C': 0.97, 'B,C': 0.95, 'D,E': 0.82, 'D,F': 0.81, 'E,F': 0.4},
        },
        'clique': {
            'names': ['A', 'B', 'C', 'D'],
            'default': 0.3,
            'pairs': {'A,B': 0.9, 'A,C': 0.9, 'B,C': 0.9},
        },
    }
    for kind, graph in graphs.items():
        path = target / kind
        if path.exists():
            shutil.rmtree(path)
        shutil.copytree(repo / 'tests/fixtures/loop_parameter_ids/line-segment', path)
        experiment = path / 'experiments/bank.edi'
        text = experiment.read_text()
        names = graph['names'] + ['unused1', 'unused2'] if kind == 'clique' else graph['names']
        for old, name in zip(['pA', 'pB', 'pC', 'pD', 'pE', 'pF'], names, strict=True):
            text = re.sub(r'(?m)^' + old + r' ', name + ' ', text)
        if kind == 'clique':
            text = re.sub(r'(?m)^(unused[12] [^\n]+)\(\)$', r'\1', text)
        experiment.write_text(text)
        count = len(graph['names'])
        analysis = path / 'analysis/analysis.edi'
        record = f"""
_fit_result.result_kind deterministic
_fit_result.success true
_fit_result.message done
_fit_result.iterations 1
_fit_result.fitting_time 0
_fit_result.reduced_chi_square 1
_fit_result.objective_name chi_square
_fit_result.objective_value {9 - count}
_fit_result.n_data_points 9
_fit_result.n_parameters 6
_fit_result.n_free_parameters {count}
_fit_result.degrees_of_freedom {9 - count}
_fit_result.covariance_available true
_fit_result.exit_reason done
_fit_result.prof_wr_factor 0.1
_fit_result.profile_function cwl-tch-pseudo-voigt
_fit_result.background_function line-segment
_fit_result.descent ladder
loop_
_fit_parameter.id
_fit_parameter.start_value
_fit_parameter.start_uncertainty
_fit_parameter.start_tied
"""
        for index, name in enumerate(graph['names']):
            record += f'bank.background.{name} {index + 4} . .\n'
        record += """loop_
_fit_parameter_correlation.id
_fit_parameter_correlation.source_kind
_fit_parameter_correlation.parameter_unique_name_i
_fit_parameter_correlation.parameter_unique_name_j
_fit_parameter_correlation.correlation
"""
        for index, (left, right) in enumerate(itertools.combinations(graph['names'], 2), 1):
            value = graph['pairs'].get(left + ',' + right, graph['default'])
            record += (
                f'{index} deterministic bank.background.{left}.intensity '
                f'bank.background.{right}.intensity {value}\n'
            )
        analysis.write_text(analysis.read_text() + record)
    (target / 'reference.json').write_text(
        json.dumps(
            {
                'source': 'Reviewed report-option seam; hand-derived '
                'strongest-correlation thresholds',
                'reference': 'diffraction-lib 0d9f10e4 display/plotting.py correlation filter',
                'graphs': graphs,
                'counts': [
                    {
                        'graph': 'pairs',
                        'requested': None,
                        'level': 0.95,
                        'kept': ['P1', 'P2', 'P3', 'P4'],
                    },
                    {
                        'graph': 'pairs',
                        'requested': 5,
                        'level': 0.95,
                        'kept': ['P1', 'P2', 'P3', 'P4'],
                    },
                    {'graph': 'pairs', 'requested': 2, 'level': 0.99, 'kept': ['P1', 'P2']},
                    {'graph': 'pairs', 'requested': 1, 'level': 0.99, 'kept': ['P1', 'P2']},
                    {'graph': 'clique', 'requested': 2, 'level': 0.9, 'kept': ['A', 'B', 'C']},
                ],
            },
            indent=2,
        )
        + '\n'
    )


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('repo', type=Path)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    generate(args.repo, args.output)
