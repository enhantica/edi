"""Execute native connection escapes across scan worker and model boundaries."""

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
        dispatch = """FitResultBase fit_by_mode(Project& project,const IterationCallback&
    on_iteration,const PreambleCallback& on_start,const CancelCallback&
    should_cancel,const FileCompleteCallback& file_complete) {
    if(project.mode=="sequential") return project.fit_sequential(on_iteration,

    on_start,{},file_complete,should_cancel);
    return project.fit_independent(on_iteration,on_start,{},file_complete,

    should_cancel);
    }"""
        expected = ['sequential:11:22:33:44', 'independent:11:22:33:44']
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
            '{},file_complete,should_cancel', '{},should_cancel,file_complete'
        )
        assert worker_dispatch(wrong, tmp_path) != expected, (
            'Scan worker wiring: subscriber identities cannot be swapped '
            'while calls remain present'
        )
    if channel == 'joint':
        model = source('src/analysis_view_model.cpp')
        marker = 'void AnalysisViewModel::sync() {'
        guarded = """
     auto tokens=edi::supported_fitting_modes();
     if(project_.sequential_fit.declared()) tokens.erase(std::remove(tokens.begin(),

    tokens.end(),"joint"),tokens.end());
     fitting_mode_options_->setOptions(tokens);"""
        good = model.replace(marker, marker + guarded)
        assert joint_options(good, tmp_path) == ['1', '0', '1'], (
            'Scan mode wiring: the guard control updates the consumed options table'
        )
        wrong = good.replace(
            'if(project_.sequential_fit.declared())', 'if(!project_.sequential_fit.declared())'
        )
        assert joint_options(wrong, tmp_path) != ['1', '0', '1'], (
            'Scan mode wiring: a scan mention on the wrong joint branch is rejected'
        )
    if channel == 'follow':
        model = source('src/project_view_model.cpp')
        selection = block(model, 'void ProjectViewModel::setCurrentExperimentIndex(')
        good = selection.replace(
            'current_experiment_ = index;',
            'fit_->setFollowing(false);\ncurrent_experiment_ = index;',
        )
        assert selection_follow(good, tmp_path) == ['0:2', '1:1', '1:1'], (
            'Follow wiring: only a changed valid manual selection turns following off'
        )
        wrong = selection.replace('publishCurrent();', 'publishCurrent();').replace(
            '    if (index !=', '    fit_->setFollowing(false);\n    if (index !='
        )
        assert selection_follow(wrong, tmp_path) != ['0:2', '1:1', '1:1'], (
            'Follow wiring: an off call outside the manual-selection branch is rejected'
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
