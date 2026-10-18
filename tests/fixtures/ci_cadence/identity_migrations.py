"""Named replacements for witnesses expanded since the shipped policy snapshot."""

BUILD = 'tests/integration/py/test_e04_t2_build_contract.py::'
SCAN = 'tests/integration/py/test_parameter_correlations.py::'
APP = 'tests/integration/py/test_correlation_app_contract.py::'

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
}
