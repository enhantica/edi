"""Explicit experiment creation and selected-data replacement preserve scientific inputs."""

import pytest

from tests.integration.app.online_load_host import run_online_host


@pytest.fixture(scope='module')
def experiment_host(tmp_path_factory):
    with run_online_host(
        tmp_path_factory.mktemp('experiment-workflow'),
        load_groups_only=True,
        failure_entries=False,
        offline_http=True,
        session_type='ExperimentWorkflowSession',
    ) as host:
        yield host


@pytest.mark.parametrize('state', ['none', 'empty', 'loaded'])
def test_measured_menu_requires_creation_and_names_load_or_replace(experiment_host, state):
    experiment_host.check('menu_state', state)


def test_create_uses_default_type_and_its_editable_selectors(experiment_host):
    experiment_host.check('default_creation')


@pytest.mark.parametrize('state', ['none', 'selected'])
def test_retired_new_experiment_type_group_is_absent(experiment_host, state):
    experiment_host.check('no_new_type_group', state)


def test_replace_preserves_parameters_matches_fresh_and_undoes(experiment_host):
    experiment_host.check('replace_model')


@pytest.mark.parametrize('route', ['file', 'web'])
def test_both_replace_actions_keep_the_selected_experiment(experiment_host, route):
    experiment_host.check('replace_ui', route)


@pytest.mark.parametrize('target', ['powder-target', 'single-crystal-target'])
def test_wrong_type_data_is_refused_without_changing_the_target(experiment_host, target):
    experiment_host.check('wrong_type', target)
