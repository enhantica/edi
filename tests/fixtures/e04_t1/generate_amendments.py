"""Create small app inputs from  and committed CLI inputs, without edi/app imports."""

from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def generate():
    source = (ROOT / 'tests/fixtures/c15_t1_xray/model.edi').read_text()
    structure, experiment = source.split('data_experiment', 1)
    # Synthetic observations: selector/UI/text coverage, not a physics reference.
    experiment = (
        'data_experiment\n_edi.schema_version 3\n'
        + experiment.strip()
        + '\n\nloop_\n_data.two_theta\n_data.intensity_meas\n_data.intensity_meas_su\n'
        '20.25 1 1\n50.25 1 1\n80.25 1 1\n\n'
        '_scattering_source.xray_form_factor it1992\n'
        '_scattering_source.xray_dispersion sasaki1989\n'
        '_background.type line-segment\n'
        'loop_\n_background.position\n_background.intensity\n20.25 0\n80.25 0\n'
    )
    for name, minimizer in [
        ('xray-project', 'crysta'),
        ('warning-project', 'legacy-e04-warning-witness'),
    ]:
        project = HERE / name
        for directory in ('structures', 'experiments', 'analysis'):
            (project / directory).mkdir(parents=True, exist_ok=True)
        (project / 'project.edi').write_text(
            '_edi.schema_version 3\n_metadata.name "E04 X-ray selector witness"\n'
        )
        (project / 'structures/structure.edi').write_text(
            structure.replace('data_structure\n', 'data_structure\n_edi.schema_version 3\n', 1)
        )
        (project / 'experiments/experiment.edi').write_text(experiment)
        (project / 'analysis/analysis.edi').write_text(
            f'_edi.schema_version 3\n_minimizer.type "{minimizer}"\n_fitting_mode.type single\n'
        )
    # A nonempty custom-length row permits an edit without assuming any append API.
    project = HERE / 'editable-project'
    original = ROOT / 'docs/user/cli/pd-neut-cwl_lbco-hrpt_start-2/project'
    for source in original.rglob('*.edi'):
        target = project / source.relative_to(original)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
    structure = project / 'structures/lbco.edi'
    structure.write_text(
        structure.read_text().replace('_edi.schema_version 2', '_edi.schema_version 3', 1)
        + '\nloop_\n_scattering_length.type_symbol\n_scattering_length.length_fm\nLa 8.24\n'
    )


if __name__ == '__main__':
    generate()
