"""Author frozen wiring regression pins via Python, never run by GUI tests.

The calculated arrays/writer text are regression pins, not independent physics goldens.
 generates and reviews these once; changes are explicit fixture diffs.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

import edi

ROOT = Path(__file__).resolve().parents[3]
PROJECTS = (
    'pd-neut-cwl_lbco-hrpt_start-2',
    'pd-neut-tof_si-sepd_start-2',
    'pd-neut-cwl_cosio-d20_start-1',
)


def generate(destination):
    destination.mkdir(parents=True, exist_ok=False)
    references = []
    for name in PROJECTS:
        project = edi.Project.load(ROOT / 'docs/user/cli' / name / 'project')
        project.calculate()
        exp = project.experiment
        data = exp.data
        axis = data.two_theta if name.startswith('pd-neut-cwl') else data.time_of_flight
        saved = destination / name
        project.save_as(saved)
        references.append({
            'project': name,
            'axis': list(axis),
            'calculated': list(data.intensity_calc),
            'texts': {
                str(p.relative_to(saved)): p.read_text()
                for p in saved.rglob('*.edi')
                if p.name != 'project.edi'
            },
        })
        shutil.rmtree(saved)  # only the reviewed JSON pins are consumed
    # URL decoding is checked on a real copied project, not on an in-memory string.
    spaced = destination / 'p q' / 'project'
    shutil.copytree(ROOT / 'docs/user/cli' / PROJECTS[0] / 'project', spaced)
    shutil.copytree(
        ROOT / 'docs/user/cli/pd-neut-tof_diamond-dream_basic/project',
        destination / 'unlisted legacy project/project',
    )
    # I15 witness changes committed input text only; no category API generates the expectation.
    unused = destination / 'unused-free'
    shutil.copytree(ROOT / 'docs/user/cli/pd-neut-tof_diamond-dream_basic/project', unused)
    file = unused / 'experiments/dream.edi'
    source = file.read_text()

    source, count = re.subn(
        r'(?m)^_peak.broad_lorentz_gamma_1\s+[^\n]+', '_peak.broad_lorentz_gamma_1 0.1()', source
    )
    if count != 1:
        raise ValueError('I15 fixture must change exactly the declared Lorentzian field')
    file.write_text(source)
    # The same upstream classic CIF tests content refusal after an extension-only rename.
    classic = Path(__file__).parent / 'classic-d20.cif'
    shutil.copyfile(classic, destination / 'd20.cif')
    shutil.copyfile(classic, destination / 'd20.edi')
    complete = (
        ROOT / 'docs/user/cli/pd-neut-tof_ncaf-wish-3bank_start-5/project/experiments/wish_2_9.edi'
    )
    for axis in ('sample_form', 'beam_mode', 'radiation_probe', 'scattering_type'):
        source, count = re.subn(
            r'(?m)^_experiment_type\.' + axis + r'[^\n]*\n', '', complete.read_text()
        )
        if count != 1:
            raise ValueError('declared-type fixture must remove exactly one axis: ' + axis)
        source = source.replace('data_wish_2_9', 'data_incomplete_' + axis, 1)
        (destination / ('missing-' + axis + '.edi')).write_text(source)
    # Directory witnesses do not need copied documentation or historical titles.
    for readme in destination.rglob('README.md'):
        readme.unlink()
    record = spaced / 'project.edi'
    record.write_text(
        re.sub(
            r'(?m)^_metadata.title.*$',
            '_metadata.title "GUI URL-decoding fixture"',
            record.read_text(),
        )
    )
    (destination / 'reference.json').write_text(
        json.dumps(references, allow_nan=False, indent=2) + '\n'
    )


if __name__ == '__main__':
    generate(Path(sys.argv[1]))
