"""Materialize the owner's position-naming witness from declared inputs.

All values and expected rounding are input/closed-form specifications. This
generator imports no product code and never captures product output as a golden.
"""

import shutil
from pathlib import Path


def main():
    root = Path(__file__).parent
    output = root / 'name-by-position'
    shutil.copytree(root / 'line-segment', output, dirs_exist_ok=True)
    analysis = output / 'analysis/analysis.edi'
    analysis.write_text(
        analysis.read_text()
        + """
loop_
_alias.id
_alias.parameter_unique_name
left bank.background.pA.intensity
right bank.background.pB.intensity

loop_
_constraint.id
_constraint.expression
bind "right = 2*left"

loop_
_fit_parameter.id
_fit_parameter.start_value
_fit_parameter.start_uncertainty
bank.background[pA] 1.25 0.375
bank.background[pB] 2.5 0.75

loop_
_fit_parameter_correlation.id
_fit_parameter_correlation.source_kind
_fit_parameter_correlation.parameter_unique_name_i
_fit_parameter_correlation.parameter_unique_name_j
_fit_parameter_correlation.correlation
_fit_parameter_correlation.file_path
pair deterministic bank.background.pA.intensity bank.background.pB.intensity -0.625 pA.xy
"""
    )


if __name__ == '__main__':
    main()
