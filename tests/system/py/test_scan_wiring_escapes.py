"""Execute native connection escapes across scan worker and model boundaries."""

from pathlib import Path

import pytest

from tests.integration.py.test_scan_app_contract import block, source
from tests.integration.py.test_scan_extended_contract import (
    fit_state,
    joint_options,
    selection_follow,
    worker_dispatch,
)


@pytest.mark.parametrize('channel', ['dispatch', 'joint', 'follow', 'state'])
def test_native_connection_observers_reject_swapped_dispatch_enabled_joint_and_wrong_follow(
    tmp_path, channel
):
    if channel == 'dispatch':
        dispatch = (Path(__file__).resolve().parents[3] / 'core/src/fit_job.cpp').read_text()
        expected = [
            'sequential:0:0:33:55:44:66',
            'independent:0:0:33:55:44:66',
            'joint scan:11:0:33:55:44:66:77',
            'joint:11:22:33',
        ]
        assert worker_dispatch(dispatch, tmp_path) == expected, (
            'Scan worker wiring: the control must forward distinct subscriber identities'
        )
        swapped = (
            dispatch
            .replace('fit_sequential', 'TEMP')
            .replace('fit_independent', 'fit_sequential')
            .replace('TEMP', 'fit_independent')
        )
        assert worker_dispatch(swapped, tmp_path) != expected, (
            'Scan worker wiring: called names on swapped branches cannot certify dispatch'
        )
        wrong = dispatch.replace(
            'on_scan_start, on_file_complete, should_cancel',
            'on_scan_start, should_cancel, on_file_complete',
        )
        assert worker_dispatch(wrong, tmp_path) != expected, (
            'Scan worker wiring: subscriber identities cannot be swapped '
            'while calls remain present'
        )
        missing_fitted = dispatch.replace('should_cancel, on_file_fitted)', 'should_cancel, {})')
        assert missing_fitted != dispatch, (
            'Scan worker wiring: the escape must remove actual fitted-project forwarding'
        )
        assert worker_dispatch(missing_fitted, tmp_path) != expected, (
            'Scan worker wiring: the fitted-project subscriber cannot disappear while '
            'row-completion and cancellation forwarding stay correct'
        )
    if channel == 'joint':
        model = source('src/analysis_view_model.cpp')
        good = model
        assert joint_options(good, tmp_path) == ['1', '1', '1'], (
            'Scan mode wiring: the guard control updates the consumed options table'
        )
        selector = (Path(__file__).resolve().parents[3] / 'core/src/selectors.cpp').read_text()
        start = selector.index('std::vector<std::string> applicable_fitting_modes(')
        scan = selector.index('if (project.sequential_fit.declared())', start)
        scan_done = selector.index('}', selector.index('return {', scan) + len('return {'))
        options = selector[scan:scan_done]
        wrong = selector[:scan] + options.replace(', "joint"', '') + selector[scan_done:]
        assert wrong != selector, (
            'Scan mode wiring: the mutation removes the Joint option from the actual scan branch'
        )
        assert joint_options(good, tmp_path, selector_text=wrong) != ['1', '1', '1'], (
            'Scan mode wiring: the probe detects the missing Joint choice on a declared scan'
        )
    if channel == 'follow':
        model = source('src/project_view_model.cpp')
        selection = block(model, 'void ProjectViewModel::setCurrentExperimentIndex(')
        good = selection
        assert selection_follow(good, tmp_path)[0] == '0:2', (
            'Follow wiring: a changed valid manual choice selects that dataset and disables Follow'
        )
        wrong = selection.replace('setFollowing(false)', 'setFollowing(true)')
        assert wrong != good, (
            'Follow wiring: the escape changes the actual manual-selection operation'
        )
        assert selection_follow(wrong, tmp_path)[0] != '0:2', (
            'Follow wiring: keeping Follow on after a changed valid manual choice is rejected'
        )
    if channel == 'state':
        header = (
            'class FitViewModel { bool scanning() const { return scanning_; } '
            'bool continuable() const { return continuable_; } };'
        )
        assert fit_state(header, '', tmp_path) == ['0:0', '1:0', '0:1'], (
            'Scan state wiring: the control distinguishes idle, running scan '
            'and stopped continuation'
        )
        assert fit_state(
            header.replace('return scanning_;', 'return scanning_ && false;'), '', tmp_path
        ) != ['0:0', '1:0', '0:1'], (
            'Scan state wiring: a disguised constant false state is rejected'
        )
