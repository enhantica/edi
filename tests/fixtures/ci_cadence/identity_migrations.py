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

# ADR-0048 consolidates the old starts and short scans into one published case.
PROJECT = 'tests/integration/app/test_e04_t1_projects.py::'
REGISTERED = 'test_each_registered_example_executes_in_the_production_host'
REPLACED_EXAMPLES = {
    'pd-neut-cwl_cosio-d20_scan-162f': 'pd-neut-cwl_cosio-d20_scan',
    'pd-neut-cwl_cosio-d20_scan-324f': 'pd-neut-cwl_cosio-d20_scan',
    'pd-neut-cwl_cosio-d20_scan-3f': 'pd-neut-cwl_cosio-d20_scan',
    'pd-neut-cwl_cosio-d20_start-1': 'pd-neut-cwl_cosio-d20',
    'pd-neut-cwl_cosio-d20_start-4': 'pd-neut-cwl_cosio-d20',
    'pd-neut-cwl_lbco-hrpt_start-2': 'pd-neut-cwl_lbco-hrpt',
    'pd-neut-cwl_lbco-hrpt_start-4': 'pd-neut-cwl_lbco-hrpt',
    'pd-neut-cwl_pbso4_beba-asymmetry': 'pd-neut-xray-cwl_pbso4-d1a-lab',
    'pd-neut-cwl_yap-spodi_3k': 'pd-neut-cwl_yalo3-al2o3-spodi',
    'pd-neut-tof_cecoal-polaris_chebyshev': 'pd-neut-tof_cecoal-polaris',
    'pd-neut-tof_ceo2-pearl_polynomial': 'pd-neut-tof_ceo2-pearl',
    'pd-neut-tof_ferrite-austenite-beer_joint': 'pd-neut-tof_ferrite-austenite-beer',
    'pd-neut-tof_ncaf-wish-2bank_start-3': 'pd-neut-tof_ncaf-wish',
    'pd-neut-tof_ncaf-wish-3bank_start-5': 'pd-neut-tof_ncaf-wish',
    'pd-neut-tof_ncaf-wish-5bank_start-5': 'pd-neut-tof_ncaf-wish',
    'pd-neut-tof_ncaf-wish-5bank_start-fullprof': 'pd-neut-tof_ncaf-wish',
    'pd-neut-tof_si-sepd_start-2': 'pd-neut-tof_si-sepd',
    'pd-neut-tof_si-sepd_start-5': 'pd-neut-tof_si-sepd',
    'pd-xray-cwl_latp_scan-4f': 'pd-xray-cwl_latp-bm01_scan',
}
MIGRATIONS.update({
    PROJECT + REGISTERED + f'[{old}]': [PROJECT + REGISTERED + f'[{new}]']
    for old, new in REPLACED_EXAMPLES.items()
})
# LaB6's verification actor remains independently exercised outside the catalogue.
MIGRATIONS[PROJECT + REGISTERED + '[pd-neut-cwl_lab6-11b-echidna_tch-fcj]'] = [
    PROJECT + 'test_verification_directory_executes_in_the_production_host'
    '[pd-neut-cwl_lab6-echidna_fcj-asymmetry]'
]
MIGRATIONS[
    'tests/integration/py/test_c34_t23_cli_projects.py::'
    'test_executing_registry_refuses_obsolete_and_malformed_ids[pd-neut-cwl_lif]'
] = [
    (
        'tests/integration/py/test_c34_t23_cli_projects.py::'
        'test_executing_registry_accepts_lowercase_page_stems_and_seed_variants[pd-neut-cwl_lif]'
    )
]
