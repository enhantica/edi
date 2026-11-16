"""The published HEiDi example declares three independent structure/data pairs."""

from pathlib import Path

import gemmi
import yaml

ROOT = Path(__file__).resolve().parents[3]
CASE = 'sc-neut-cwl_cosio-heidi'


def block(path):
    source = path.read_text()
    return gemmi.cif.read_string(
        source if source.startswith('data_') else 'data_input\n' + source
    ).sole_block()


def test_heidi_example_uses_independent_experiments_without_a_scan():
    records = yaml.safe_load((ROOT / 'docs/user/cli/projects.yml').read_text())['projects']
    assert len([row for row in records if row['id'] == CASE]) == 1, (
        'The three-temperature HEiDi example has exactly one declared case record'
    )
    project = ROOT / 'docs/user/cli' / CASE / 'project'
    analysis = project / 'analysis/analysis.edi'
    assert analysis.is_file(), 'The HEiDi example supplies its complete fitting-mode input'
    model = block(analysis)
    assert model.find_value('_fitting_mode.type') == 'independent', (
        'The three-temperature HEiDi example fits its experiments independently'
    )
    assert not model.find_value('_sequential_fit.data_dir'), (
        'The HEiDi example uses independent experiments, not a file scan'
    )
    structures = [
        p for p in (project / 'structures').iterdir() if p.suffix in {'.edi', '.cif', '.mcif'}
    ]
    experiments = sorted((project / 'experiments').glob('*.edi'))
    assert len(structures) == len(experiments) == 3, (
        'The HEiDi example holds one structure and one dataset at each of its three temperatures'
    )
    names = {block(path).name for path in structures}
    linked = []
    for path in experiments:
        dataset = block(path)
        assert (
            gemmi.cif.as_string(dataset.find_value('_experiment_type.sample_form'))
            == 'single crystal'
        ), 'Each HEiDi dataset is a single-crystal experiment'
        assert (
            gemmi.cif.as_string(dataset.find_value('_experiment_type.radiation_probe'))
            == 'neutron'
        ), 'Each HEiDi dataset retains its neutron-scattering measurement'
        links = list(dataset.find_values('_linked_structure.structure_id'))
        assert len(links) == 1, 'Each independent HEiDi dataset links exactly its own structure'
        linked.extend(links)
    assert len(set(linked)) == 3 and set(linked) == names, (
        'The three HEiDi links form a bijection onto their own three structures'
    )
