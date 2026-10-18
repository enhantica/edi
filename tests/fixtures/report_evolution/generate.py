"""Declare a small scan and its independent six-parameter result ledger."""

import csv
import json
import shutil
from pathlib import Path


def main():
    target = Path(__file__).parent
    repo = target.parents[2]
    project = target / 'project'
    if project.exists():
        shutil.rmtree(project)
    shutil.copytree(repo / 'tests/fixtures/report_options/pairs', project)
    temperatures = [293.15, 311.75, 337.25]
    names = [f'bank.background.P{i}.intensity' for i in range(1, 7)]
    analysis = project / 'analysis/analysis.edi'
    text = analysis.read_text().replace(
        '_fitting_mode.type single', '_fitting_mode.type sequential'
    )
    text += '\n_sequential_fit.data_dir scan\n_sequential_fit.file_pattern *.dat\n'
    text += '_sequential_fit.template_file point1.dat\n'
    text += (
        'loop_\n_sequential_fit_extract.id\n_sequential_fit_extract.target\n'
        '_sequential_fit_extract.pattern\n_sequential_fit_extract.required\n'
        'T diffrn.ambient_temperature ^TEMP\\s+([0-9.]+) true\n'
    )
    analysis.write_text(text)
    (project / 'scan').mkdir()
    rows = []
    for i, temperature in enumerate(temperatures):
        filename = f'point{i + 1}.dat'
        (project / 'scan' / filename).write_text(
            f'TEMP {temperature}\n40 5 1\n44 6 1\n48 7 1\n52 8 1\n56 9 1\n'
            '60 10 1\n64 11 1\n68 12 1\n72 13 1\n'
        )
        values = [
            value for p in range(6) for value in (4.30925 + p + i * 0.125, 0.00157 + p * 0.0001)
        ]
        rows.append([f'scan/{filename}', 1, True, 1, temperature, *values])
    with (project / 'analysis/results.csv').open('w', newline='') as output:
        writer = csv.writer(output)
        writer.writerow([
            'file_path',
            'fit_result.reduced_chi_square',
            'fit_result.success',
            'fit_result.iterations',
            'diffrn.ambient_temperature',
            *[column for name in names for column in (name, name + '.uncertainty')],
        ])
        writer.writerows(rows)
    hand_series = [
        {
            'name': name,
            'x': temperatures,
            'y': [row[5 + 2 * p] for row in rows],
            'error_y': {'visible': True, 'array': [row[6 + 2 * p] for row in rows]},
        }
        for p, name in enumerate(names)
    ]
    positive = '<!doctype html><style>body{margin:8px}.evolution-figure{display:grid;'
    positive += 'grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}'
    positive += '.js-plotly-plot{height:160px}@media(max-width:500px){.evolution-figure{'
    positive += 'grid-template-columns:1fr}}</style><div class="evolution-figure">'
    positive += '<div class="js-plotly-plot"><svg width="20" height="20"></svg></div>' * 6
    positive += '</div><script>const independent=' + json.dumps(hand_series) + ';'
    positive += 'document.querySelectorAll(".js-plotly-plot").forEach((plot,i)=>{'
    positive += 'plot.data=[independent[i]];plot.layout={xaxis:{title:{text:"Temperature (K)"}},'
    positive += 'yaxis:{title:{text:independent[i].name}}};});</script>'
    (target / 'browser-positive.html').write_text(positive)
    root_positive = positive.replace('.evolution-figure', '.evolution-grid')
    root_positive = root_positive.replace('class="evolution-figure"', 'class="evolution-grid"')
    root_positive = root_positive.replace(
        'class="js-plotly-plot"', 'class="evolution-figure js-plotly-plot"'
    )
    (target / 'browser-positive-root.html').write_text(root_positive)
    (target / 'reference.json').write_text(
        json.dumps(
            {
                'source': 'Hand-declared six free parameters and three temperatures',
                'names': names,
                'x': temperatures,
                'points': [
                    [
                        {'x': temperature, 'y': rows[i][5 + 2 * p], 'su': rows[i][6 + 2 * p]}
                        for i, temperature in enumerate(temperatures)
                    ]
                    for p in range(6)
                ],
            },
            indent=2,
        )
        + '\n'
    )


if __name__ == '__main__':
    main()
