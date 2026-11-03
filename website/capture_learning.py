#!/usr/bin/env python3
"""Generate measured/starting/refined plots from the same selected example as the GUI."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path
from urllib.parse import unquote

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent

# Executed in the app environment, against a disposable copy of the selected project.
RUN = """
import json, math, shutil, sys
from pathlib import Path
import edi
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from plotly.offline import get_plotlyjs
source, output, example = map(Path, sys.argv[1:4])
refined_path = Path(sys.argv[4]) if len(sys.argv) > 4 else None
project_path = output / example
shutil.copytree(source, project_path)
project = edi.Project.load(project_path)
experiment = project.experiments[0]
project.analysis.calculate()
data = experiment.data
if not hasattr(data, 'two_theta'):
    raise RuntimeError('This learning comparison requires a constant-wavelength powder example')
x = list(data.two_theta)
measured = list(data.intensity_meas)
initial = list(data.intensity_calc)
if refined_path is None:
    result = project.analysis.fit()
    if not result.success:
        raise RuntimeError('The learning example did not fit successfully')
    result_info = {'rwp':result.rwp,'reduced_chi_square':result.reduced_chi_square,\
'converged':result.converged}
    refined = list(experiment.data.intensity_calc)
else:
    final = edi.Project.load(refined_path)
    final.analysis.calculate()
    final_data = final.experiments[0].data
    if list(final_data.two_theta) != x or list(final_data.intensity_meas) != measured:
        raise RuntimeError('GUI checkpoints must contain identical observations')
    refined = list(final_data.intensity_calc)
    fields = {}
    for line in (refined_path/'analysis/analysis.edi').read_text().splitlines():
        parts = line.split()
        if len(parts)==2 and parts[0].startswith('_fit_result.'):
            fields[parts[0].split('.',1)[1]] = parts[1]
    if fields.get('success') != 'true':
        raise RuntimeError('The GUI refinement did not report success')
    result_info = {'rwp':float(fields['prof_wr_factor']),\
'reduced_chi_square':float(fields['reduced_chi_square']),'success':True,\
'exit_reason':fields.get('exit_reason')}

finite = [value for value in measured+initial+refined if math.isfinite(value)]
ymin, ymax = min(finite), max(finite)
margin = (ymax-ymin)*.04
residual_max = max(abs(y-predicted) for curve in (initial,refined) for y,predicted in \
zip(measured,curve) if math.isfinite(y) and math.isfinite(predicted))
plots = {}
for name, calculated in [('initial',initial), ('refined',refined)]:
    figure = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[.74,.26], \
vertical_spacing=.06)
    figure.add_trace(go.Scatter(x=x,y=measured,name='Measured',mode='lines',\
line=dict(color='#0084c7',width=1.4)), row=1,col=1)
    figure.add_trace(go.Scatter(x=x,y=calculated,name='Calculated',mode='lines',\
line=dict(color='#d13f73',width=1.1)), row=1,col=1)
    figure.add_trace(go.Scatter(x=x,y=[y-c for y,c in zip(measured,calculated)],name='Residual',\
mode='lines',line=dict(color='#777777',width=1)),row=2,col=1)
    figure.update_layout(template='plotly_white',width=1000,height=540,margin=dict(l=85,r=25,t=45,\
b=55),legend=dict(orientation='h',y=1.12),font=dict(family='Arial',size=14))
    figure.update_yaxes(title_text='Intensity',range=[ymin-margin,ymax+margin],row=1,col=1)
    figure.update_yaxes(title_text='Residual',range=[-residual_max*1.05,residual_max*1.05],row=2,\
col=1)
    figure.update_xaxes(range=[min(x),max(x)])
    figure.update_xaxes(title_text='2θ (°)',row=2,col=1)
    plots[name] = json.loads(figure.to_json())
(output/'plot-data.json').write_text(json.dumps({'example':str(example),'plots':plots,\
'result':result_info,'edi_build_commit':edi.__build_commit__,\
'axis_ranges':{name:{axis:plot['layout'][axis]['range'] for axis in ['xaxis','xaxis2','yaxis',\
'yaxis2']} for name,plot in plots.items()}}))
(output/'plotly.js').write_text(get_plotlyjs())
"""


def _export_svgs(work: Path, document: dict, output: Path) -> None:
    """Render the Plotly figures to SVG files in a headless browser."""
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=os.environ.get('BROWSER_EXECUTABLE', 'chromium'),
            args=['--no-sandbox', '--disable-dev-shm-usage'],
        )
        try:
            page = browser.new_page()
            page.set_content('<div id="plot"></div>')
            page.add_script_tag(path=str(work / 'plotly.js'))
            for name, plot in document.pop('plots').items():
                svg_url = page.evaluate(
                    """async figure => {
                        await Plotly.newPlot('plot',figure.data,figure.layout,{staticPlot:true});
                        return await Plotly.toImage('plot',{format:'svg',width:1000,height:540});
                    }""",
                    plot,
                )
                encoded = svg_url.split(',', 1)[1]
                svg = (
                    base64.b64decode(encoded)
                    if ';base64,' in svg_url
                    else unquote(encoded).encode()
                )
                (output / f'{name}.svg').write_bytes(svg)
        finally:
            browser.close()


def _write_transcript(edi_root: Path, source: Path, env: dict, output: Path) -> None:
    command = [
        str(edi_root / '.pixi/envs/app/bin/python'),
        '-m',
        'edi',
        'fit',
        str(source),
        '--dry',
    ]
    result = subprocess.run(command, check=True, text=True, capture_output=True, env=env)
    (output / 'command-line.txt').write_text(
        '\n'.join(line.rstrip() for line in result.stdout.splitlines()) + '\n'
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--edi-root', required=True, type=Path)
    parser.add_argument('--gui-capture', type=Path)
    args = parser.parse_args()
    edi_root = args.edi_root.resolve()
    output = ROOT / 'surfaces/docs/assets/learning'
    if args.gui_capture:
        output /= 'gui'
    output.mkdir(parents=True, exist_ok=True)
    fixture = json.loads((ROOT / 'surfaces/docs/assets/gui/y2o3/manifest.json').read_text())
    example = fixture['example']
    source = edi_root / 'docs/user/cli' / example / 'project'
    refined_source = None
    if args.gui_capture:
        capture = args.gui_capture.resolve()
        manifest = json.loads((capture / 'manifest.json').read_text())
        if manifest['example'] != example or manifest['status'] != 'complete':
            raise ValueError('A completed capture of the selected example is required')
        source = capture / 'checkpoints/starting'
        refined_source = capture / 'checkpoints/refined'
    env = {
        **os.environ,
        'PYTHONPATH': str(edi_root / 'lib'),
        'EDI_EXTENSION_DIR': str(edi_root / 'build/assistant-dev/python/edi'),
        'LD_LIBRARY_PATH': str(edi_root / '.pixi/envs/app/lib'),
    }
    with tempfile.TemporaryDirectory(prefix='edi-learning-') as temporary:
        work = Path(temporary)
        run = [
            str(edi_root / '.pixi/envs/app/bin/python'),
            '-c',
            RUN,
            str(source),
            str(work),
            example,
        ]
        if refined_source:
            run.append(str(refined_source))
        subprocess.run(run, check=True, env=env)
        document = json.loads((work / 'plot-data.json').read_text())
        _export_svgs(work, document, output)
        _write_transcript(edi_root, source, env, output)
    document['generator_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    document['input_sha256'] = {
        str(path.relative_to(source)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(source.rglob('*'))
        if path.is_file()
    }
    if refined_source:
        document['refined_input_sha256'] = {
            str(path.relative_to(refined_source)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted(refined_source.rglob('*'))
            if path.is_file()
        }
        document['gui_capture'] = {
            'source_revision': manifest['source_revision'],
            'binary_sha256': manifest['binary_sha256'],
            'manifest_sha256': hashlib.sha256(
                (capture / 'manifest.json').read_bytes()
            ).hexdigest(),
        }
    document['assets_sha256'] = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(output.glob('*.svg'))
    }
    (output / 'capture.json').write_text(json.dumps(document, indent=2) + '\n')
    print(json.dumps(document['result']))


if __name__ == '__main__':
    main()
