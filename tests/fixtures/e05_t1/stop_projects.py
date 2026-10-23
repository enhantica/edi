"""Declared stop inputs: a zero column and a domain-blocked positive-gain column."""

import shutil
from pathlib import Path


def materialize(engine, source, target, *, stalled):
    """Write a disposable LBCO input with an independently declared stop condition."""
    target = Path(target)
    if target.exists():
        shutil.rmtree(target)
    project = engine.Project.load(str(source))
    for parameter in project.parameters:
        parameter.free = False
    for site in project.structure.atom_sites:
        site.occupancy.value = 0.0
    driver = project.structure.atom_sites[0].adp_iso
    driver.value = 0.0 if stalled else 0.5
    driver.free = True
    project.save_as(str(target))
    (target / 'README.md').unlink(missing_ok=True)
    if not stalled:
        return target

    experiment = target / 'experiments/hrpt.edi'
    prefix, separator, _old = experiment.read_text().partition('_background.type ')
    if not separator:
        message = 'the LBCO stop input must declare its background'
        raise ValueError(message)
    experiment.write_text(
        prefix
        + """_background.type line-segment

loop_
_background.id
_background.position
_background.intensity
left 35 0
right 85 0

loop_
_data.two_theta
_data.intensity_meas
_data.intensity_meas_su
40 -1 1
60 -1 1
80 -1 1
"""
    )
    (target / 'analysis/analysis.edi').write_text("""_edi.schema_version 3
_fitting_mode.type single
_minimizer.type crysta
_minimizer.max_iterations 3
_minimizer.chi_square_tolerance 1e-6

loop_
_alias.id
_alias.parameter_unique_name
driver lbco.atom_site.La.adp_iso
left hrpt.background.left.intensity
right hrpt.background.right.intensity
fraction hrpt.preferred_orientation.lbco.march_random_fract

loop_
_constraint.id
_constraint.expression
_constraint.enabled
left_value "left = driver" true
right_value "right = driver" true
fraction_value "fraction = driver" true
""")
    return target
