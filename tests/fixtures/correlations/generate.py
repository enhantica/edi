"""Freeze an independent polynomial covariance and diffraction-lib heatmap."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import runpy
import subprocess
from contextlib import suppress
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import plotly.graph_objects as go

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def methods(path, names):
    tree = ast.parse(path.read_text())
    selected = [
        node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef) and node.name in names
    ]
    if {node.name for node in selected} != set(names):
        raise ValueError('The reference checkout does not contain every requested method')
    return selected


class MatrixFrame:
    def __init__(self, matrix, names):
        self.matrix = matrix
        self.shape = matrix.shape
        self.columns = np.asarray(names)
        self.index = np.asarray(names)

    def to_numpy(self, **_kwargs):
        return self.matrix


def generate(reference_root):  # noqa: PLR0912, PLR0914, PLR0915 - one authoring workflow
    analysis_path = reference_root / 'src/easydiffraction/analysis/analysis.py'
    plotter_path = reference_root / 'src/easydiffraction/display/plotters/plotly.py'
    facade_path = reference_root / 'src/easydiffraction/display/plotting.py'
    analysis_methods = methods(
        analysis_path,
        [
            '_correlation_matrix_from_covariance',
            '_store_correlation_projection',
        ],
    )
    plotter_methods = methods(
        plotter_path,
        [
            'plot_correlation_heatmap',
            '_get_correlation_label_trace',
            '_correlation_colorscale_for_background',
            '_correlation_label_color',
        ],
    )
    facade_tree = ast.parse(facade_path.read_text())
    facade_class = next(
        node
        for node in facade_tree.body
        if isinstance(node, ast.ClassDef) and node.name == 'Plotter'
    )
    available = {
        node.name: node for node in facade_class.body if isinstance(node, ast.FunctionDef)
    }
    selected = {'_build_correlation_heatmap_plot'}
    pending = list(selected)
    overrides = {'_plot_axis_frame_color', '_plot_correlation_colorscale'}
    while pending:
        for node in ast.walk(available[pending.pop()]):
            if (
                isinstance(node, ast.Attribute)
                and isinstance(node.value, ast.Name)
                and node.value.id in {'self', 'cls', 'Plotter'}
                and node.attr in available
                and node.attr not in selected | overrides
            ):
                selected.add(node.attr)
                pending.append(node.attr)
    context = next(
        node
        for node in facade_tree.body
        if isinstance(node, ast.ClassDef) and node.name == '_CorrelationHeatmapContext'
    )
    source = (
        'from __future__ import annotations\nfrom dataclasses import dataclass\n'
        'import numpy as np\nimport plotly.graph_objects as go\n'
    )
    source += ast.unparse(context) + '\n'
    source += (
        ast.unparse(
            ast.ClassDef(
                name='Plotter',
                bases=[],
                keywords=[],
                body=[available[name] for name in sorted(selected)],
                decorator_list=[],
            )
        )
        + '\n'
    )
    for name, nodes in [
        ('AnalysisReference', analysis_methods),
        ('PlotterReference', plotter_methods),
    ]:
        source += (
            ast.unparse(
                ast.ClassDef(name=name, bases=[], keywords=[], body=nodes, decorator_list=[])
            )
            + '\n'
        )
    (HERE / 'reference_methods.txt').write_text(source)
    namespace = {'__name__': __name__}
    for path in [plotter_path, facade_path]:
        for node in ast.parse(path.read_text()).body:
            if (
                isinstance(node, ast.ImportFrom)
                and node.module == 'easydiffraction.display.plotters.plotly'
            ):
                for alias in node.names:
                    if alias.name in namespace:
                        namespace[alias.asname or alias.name] = namespace[alias.name]
            if (
                isinstance(node, ast.Assign)
                and all(isinstance(target, ast.Name) for target in node.targets)
                and not any(isinstance(part, ast.Call) for part in ast.walk(node.value))
            ):
                with suppress(NameError, AttributeError):
                    exec(  # noqa: S102 - execute frozen upstream methods only at authoring time
                        compile(ast.Module(body=[node], type_ignores=[]), str(path), 'exec'),
                        namespace,
                    )
    exec(  # noqa: S102 - execute frozen upstream methods only at authoring time
        compile(source, str(HERE / 'reference_methods.txt'), 'exec'), namespace
    )
    projection = namespace['AnalysisReference']()
    plotter = namespace['PlotterReference']()
    namespace['PlotlyPlotter'] = namespace['PlotterReference']
    namespace['PlotlyPlotter']._apply_theme_sync_meta = lambda *_args, **_kwargs: None
    facade = namespace['Plotter']()
    facade._plot_axis_frame_color = lambda: '#444444'
    facade._plot_correlation_colorscale = lambda: plotter._correlation_colorscale_for_background(
        '#ffffff'
    )
    plotter._correlation_colorscale = lambda: plotter._correlation_colorscale_for_background(
        '#ffffff'
    )
    plotter._correlation_grid_color = lambda: '#444444'
    plotter._get_layout = lambda title, _axes, shapes: go.Layout(title=title, shapes=shapes)
    plotter._get_figure = lambda traces, layout: go.Figure(data=traces, layout=layout)
    plotter._apply_theme_sync_meta = lambda *_args, **_kwargs: None
    figures = []
    plotter._show_figure = figures.append
    materialize = runpy.run_path(str(ROOT / 'tests/fixtures/constraint_expressions/project.py'))[
        'materialize'
    ]
    result = {
        'reference_revision': subprocess.check_output(
            ['git', '-C', str(reference_root), 'rev-parse', 'HEAD'], text=True
        ).strip(),
        'reference_sources': {
            str(p.relative_to(reference_root)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in [analysis_path, plotter_path, facade_path]
        },
        'method': (
            'Unit-weight polynomial least squares: inverse(X.T @ X), '
            'normalized by diffraction-lib; no product engine imported.'
        ),
        'cases': {},
    }
    t = np.arange(9, dtype=float) / 10
    for count in (1, 2, 3):
        design = np.column_stack([t**power for power in range(count)])
        covariance = np.linalg.inv(design.T @ design)
        noise = np.asarray([(-1) ** index / 10 for index in range(len(t))])
        residual = noise - design @ covariance @ design.T @ noise
        observed = 5 + 2 * t + 3 * t * t + residual
        correlation = projection._correlation_matrix_from_covariance(covariance)
        names = [f'bank.background.{name}.coef' for name in ('base', 'ramp', 'curve')[:count]]
        rows = []
        projection.fit_parameter_correlations = SimpleNamespace(
            create=lambda _rows=rows, **kwargs: _rows.append(kwargs)
        )
        projection._store_correlation_projection(
            unique_names=names,
            correlation_matrix=correlation,
            source_kind=SimpleNamespace(value='deterministic'),
        )
        case = {'names': names, 'matrix': correlation.tolist(), 'rows': rows}
        result['cases'][str(count)] = case
        (HERE / f'matrix-{count}.txt').write_text(
            str(count)
            + '\n'
            + '\n'.join(names)
            + '\n'
            + '\n'.join(' '.join(f'{value:.17g}' for value in row) for row in correlation)
            + '\n'
        )
        directory = materialize(
            HERE / f'polynomial-{count}',
            polynomial=True,
            observations=list(zip(40 * (1 + t), observed, strict=True)),
        )
        experiment = directory / 'experiments/bank.edi'
        text = experiment.read_text()
        if 'base 0 4()\nramp 1 1()\ncurve 2 3\n' not in text:
            raise ValueError('The polynomial vehicle must carry its three declared row identities')
        text = text.replace('ramp 1 1()', 'ramp 1 ' + ('1()' if count > 1 else '2'))
        text = text.replace('curve 2 3\n', 'curve 2 ' + ('2()' if count > 2 else '3') + '\n')
        experiment.write_text(text)
        loop = (
            'loop_\n_fit_parameter_correlation.id\n_fit_parameter_correlation.source_kind\n'
            '_fit_parameter_correlation.parameter_unique_name_i\n'
            '_fit_parameter_correlation.parameter_unique_name_j\n'
            '_fit_parameter_correlation.correlation\n'
        )
        loop += ''.join(
            f'{index + 1} deterministic {row["parameter_unique_name_i"]} '
            f'{row["parameter_unique_name_j"]} {row["correlation"]:.17g}\n'
            for index, row in enumerate(rows)
        )
        (HERE / f'loop-{count}.edi').write_text(loop if rows else '')
        displayed = correlation.copy()
        displayed[np.triu_indices(count)] = np.nan
        figures.append(
            facade._build_correlation_heatmap_plot(
                MatrixFrame(displayed, names),
                'Polynomial parameter correlations',
                threshold=None,
                precision=3,
            )
        )
    figure = figures[-1]
    (HERE / 'heatmap.json').write_text(figure.to_json() + '\n')
    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="660" height="520" viewBox="0 0 660 520">',
        '<rect width="660" height="520" fill="white"/>',
    ]
    matrix = np.asarray(result['cases']['3']['matrix'])
    endpoints = [np.asarray([215, 48, 39]), np.asarray([69, 117, 180])]
    for row in range(3):
        for column in range(3):
            if column >= row:
                continue
            value = matrix[row, column]
            magnitude = min(abs(value), 1.0)
            rgb = np.rint(255 * (1 - magnitude) + endpoints[int(value >= 0)] * magnitude).astype(
                int
            )
            colour = '#' + ''.join(f'{channel:02x}' for channel in rgb)
            svg.extend([
                (
                    f'<rect x="{180 + 110 * column}" y="{40 + 110 * row}" '
                    f'width="110" height="110" fill="{colour}" stroke="#444444"/>'
                ),
                (
                    f'<text x="{235 + 110 * column}" y="{99 + 110 * row}" '
                    'text-anchor="middle" fill="#f5f5f5" font-family="sans-serif">'
                    f'{value:.3f}</text>'
                ),
            ])
    for index, name in enumerate(result['cases']['3']['names']):
        svg.extend([
            (
                f'<text x="170" y="{99 + 110 * index}" text-anchor="end" '
                f'font-family="sans-serif" font-size="11">{name}</text>'
            ),
            (
                f'<text transform="translate({235 + 110 * index},385) rotate(25)" '
                f'font-family="sans-serif" font-size="11">{name}</text>'
            ),
        ])
    svg.append('</svg>')
    (HERE / 'heatmap.svg').write_text('\n'.join(svg) + '\n')
    result['heatmap'] = {
        'colorscale': list(figure.data[0].colorscale),
        'zmin': -1,
        'zmax': 1,
        'zmid': 0,
        'shape_count': len(figure.layout.shapes),
    }
    (HERE / 'reference.json').write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('reference_root', type=Path)
    generate(parser.parse_args().reference_root)
