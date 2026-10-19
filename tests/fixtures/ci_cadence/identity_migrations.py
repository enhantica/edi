"""Named replacements for witnesses expanded since the shipped policy snapshot."""

BUILD = 'tests/integration/py/test_e04_t2_build_contract.py::'
SCAN = 'tests/integration/py/test_parameter_correlations.py::'
APP = 'tests/integration/py/test_correlation_app_contract.py::'
ROUTES = 'tests/system/py/test_c13_t14_fast_ci_routes.py::'

MIGRATIONS = {
    **{
        BUILD + f'test_desktop_ci_sequence_builds_once_before_checks[{platform}]': [
            BUILD
            + f'test_desktop_ci_sequence_builds_once_before_checks[{event}-{enabled}-{platform}]'
            for event, enabled in (
                ('pull_request', False),
                ('push', False),
                ('schedule', True),
                ('workflow_dispatch', True),
            )
        ]
        for platform in ('Linux', 'macOS')
    },
    **{
        SCAN
        + 'test_scan_persists_only_declared_templates_external_pairs_on_save_and_reload'
        + f'[{mode}]': [
            SCAN
            + 'test_scan_persists_effective_templates_external_pairs_on_save_and_reload'
            + f'[{template}-{mode}]'
            for template in ('first-by-default', 'declared-first', 'declared-later')
        ]
        for mode in ('sequential', 'independent')
    },
    APP + 'test_diagnostics_uses_a_button_with_a_declared_combobox_width': [
        APP + 'test_diagnostics_uses_the_preferences_shared_control_width'
    ],
    **{
        ROUTES
        + 'test_nightly_only_observers_are_absent_from_actual_pr_shards_and_retained_nightly'
        + f'[{platform}-{event}]': [
            ROUTES
            + 'test_nightly_only_observers_are_absent_from_actual_pr_shards_and_retained_nightly'
            + f'[{platform}-{event}-False]'
        ]
        for platform in ('Linux', 'macOS')
        for event in ('pull_request', 'push', 'schedule')
    },
    **{
        'tests/system/py/test_e09_t58_cli_persistence.py::' + previous: [
            'tests/system/py/test_e09_t58_cli_persistence.py::'
            'test_edi_all_accepted_axis_prior_arrangements_survive_saved_undo[' + kinds + ']'
        ]
        for previous, kinds in (
            ('test_edi_nonfirst_free_axis_prior_survives_saved_undo', 'fixed-positive-fixed'),
            (
                'test_edi_mixed_optional_axis_priors_survive_saved_undo[absent-zero-fixed]',
                'absent-zero-fixed',
            ),
            (
                'test_edi_mixed_optional_axis_priors_survive_saved_undo[zero-absent-fixed]',
                'zero-absent-fixed',
            ),
        )
    },
}
