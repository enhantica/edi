"""Declare scale-only corpus cases using the independent weighted normal equation."""

from __future__ import annotations

import json
import re
import shutil
from decimal import Decimal, localcontext
from pathlib import Path

HERE = Path(__file__).resolve().parent
CORPUS = HERE.parents[1] / 'fitting'


def main():
    references = json.loads((HERE / 'fullprof.json').read_text())['cases']
    for name, reference in references.items():
        if 'extinction' in name:
            continue
        case_id = name.replace('sc-neut-', 'single-crystal-').replace('_', '-')
        destination = CORPUS / case_id
        destination.mkdir(parents=True, exist_ok=True)
        shutil.copytree(HERE / 'projects' / name, destination / 'project', dirs_exist_ok=True)
        experiment = destination / 'project/experiments/experiment.edi'
        text = experiment.read_text()
        scale = Decimal(re.search(r'^structure (\S+)$', text, re.MULTILINE)[1])
        text = text.replace(f'structure {scale}\n', f'structure {scale * Decimal(".71")}()\n')
        experiment.write_text(text)
        analysis = destination / 'project/analysis/analysis.edi'
        analysis.parent.mkdir(exist_ok=True)
        analysis.write_text(
            '_edi.schema_version 3\n_fitting_mode.type single\n'
            '_minimizer.max_iterations 100\n_minimizer.chi_square_tolerance 1e-10\n'
        )
        with localcontext() as context:
            context.prec = 50
            basis = [Decimal(str(row['f2_calc'])) / scale for row in reference['calculated_rows']]
            measured = [Decimal(str(row[3])) for row in reference['input_rows']]
            sigma = [Decimal(str(row[4])) for row in reference['input_rows']]
            normal = sum((f / s) ** 2 for f, s in zip(basis, sigma, strict=True))
            fitted = (
                sum(f * y / s**2 for f, y, s in zip(basis, measured, sigma, strict=True)) / normal
            )
            reduced = sum(
                ((y - fitted * f) / s) ** 2 for f, y, s in zip(basis, measured, sigma, strict=True)
            ) / (len(basis) - 1)
            quantities = {
                'n_free': (1, 0, None),
                'n_points_fitted': (len(basis), 0, None),
                'param.scale.value': (float(fitted), 2e-5, 2e-4),
                'reduced_chi_square': (float(reduced), None, 3e-4),
            }
        (destination / 'reference.json').write_text(json.dumps(reference, indent=2) + '\n')
        (destination / 'expected.json').write_text(
            json.dumps(
                {
                    'schema': 1,
                    'source': {
                        'engine': 'Weighted normal equation on FullProf F²',
                        'artifact': 'reference.json',
                        'provenance': 'PROVENANCE.md',
                    },
                    'quantities': {
                        key: {
                            'value': value,
                            'kind': 'reference',
                            'tol_abs': absolute,
                            'tol_rel': relative,
                        }
                        for key, (value, absolute, relative) in quantities.items()
                    },
                },
                indent=2,
            )
            + '\n'
        )
        (destination / 'PROVENANCE.md').write_text(
            '# Scale-only weighted fit\n\n'
            'The input structure and calculated basis come from the frozen FullProf files in\n'
            '`tests/fixtures/single_crystal`. All measured reflections participate. The\n'
            'single free scale starts at 0.71 times the PCR scale. The reference optimum is\n'
            '`sum(F * measured / sigma²) / sum(F² / sigma²)`, with F the FullProf\n'
            'calculated intensity divided by the PCR scale. Reduced chi-square is the\n'
            'residual sum divided by N minus one. Decimal arithmetic uses 50 digits.\n\n'
            'The tolerances admit the four-decimal FullProf output quantization. These\n'
            'values are independent normal-equation references, not FullProf fitted\n'
            'parameters or engine regression pins. Generate with\n'
            '`tests/fixtures/single_crystal/generate_fit_cases.py`.\n'
        )
        print(case_id)


if __name__ == '__main__':
    main()
