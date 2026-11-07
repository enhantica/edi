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

# The status-bar warning moved into the result banner; the real Qt actor exercises both scan modes.
MIGRATIONS[
    'tests/system/py/test_scan_projection_wiring_escapes.py::'
    'test_actual_stale_markers_reject_constant_or_other_result_state[status]'
] = [
    'tests/system/py/test_status_fit_controls.py::'
    f'test_status_fit_contract[test_outdated_results_banner:{mode}]'
    for mode in ('sequential', 'independent')
]


# The combined native forwarding witness exceeded the integration bound.
MIGRATIONS[
    'tests/integration/py/test_scan_app_contract.py::'
    'test_forwarding_controls_reject_wrong_selected_index_token_range_and_visibility'
] = [
    (
        'tests/system/py/test_scan_forwarding_controls.py::'
        'test_forwarding_controls_reject_wrong_selected_index_token_range_and_visibility'
    )
]


# Archive and resource controls retain their identities in the system tier.
SCAN_DELIVERY_NODES = (
    'test_bundled_project_load_and_save_as_use_the_writable_copy_routes',
    'test_effective_bundle_contains_selected_scan_payloads[desktop]',
    'test_effective_bundle_contains_selected_scan_payloads[web]',
    'test_resource_observer_rejects_comment_only_and_inactive_bundle_calls',
    'test_resource_observer_rejects_wrong_prefix_target_metadata_index_and_hidden_web_payload[prefix]',
    'test_resource_observer_rejects_wrong_prefix_target_metadata_index_and_hidden_web_payload[target]',
    'test_resource_observer_rejects_wrong_prefix_target_metadata_index_and_hidden_web_payload[metadata]',
    'test_resource_observer_rejects_wrong_prefix_target_metadata_index_and_hidden_web_payload[alias]',
    'test_resource_observer_rejects_wrong_prefix_target_metadata_index_and_hidden_web_payload[index]',
    'test_resource_observer_rejects_wrong_prefix_target_metadata_index_and_hidden_web_payload[hidden]',
    'test_resource_observer_refuses_non_compilation_target_sources[resource.dat]',
    'test_resource_observer_refuses_non_compilation_target_sources[resource.qrc]',
    'test_resource_observer_refuses_non_compilation_target_sources["$<IF:$<BOOL:1>,resource.dat,source.cpp>"]',
    'test_working_copy_observer_rejects_copy_to_an_unrelated_destination',
    'test_resource_observer_accepts_a_separately_linked_example_library',
    'test_resource_observer_rejects_excluded_payload_in_the_live_qml_module[default]',
    'test_resource_observer_rejects_excluded_payload_in_the_live_qml_module[prefix]',
    'test_resource_observer_rejects_excluded_payload_in_the_live_qml_module[alias]',
    'test_resource_observer_distinguishes_executable_and_library_interfaces[PRIVATE]',
    'test_resource_observer_distinguishes_executable_and_library_interfaces[PUBLIC]',
    'test_resource_observer_distinguishes_executable_and_library_interfaces[INTERFACE]',
    'test_resource_observer_distinguishes_executable_and_library_interfaces[library-interface]',
    'test_resource_observer_rejects_a_second_payload_at_the_index_address',
)
MIGRATIONS.update({
    'tests/integration/py/test_scan_extended_contract.py::' + node: [
        'tests/system/py/test_scan_collection_delivery.py::' + node
    ]
    for node in SCAN_DELIVERY_NODES
})


# External scan sources supersede the former containment expectation.
LINKED_SCANS = 'tests/system/py/test_c11_t43_rejection_classes.py::'
MIGRATIONS.update({
    LINKED_SCANS + old + f'[{argument}]': [LINKED_SCANS + new + f'[{argument}]']
    for old, new, arguments in (
        (
            'test_edi_data_dir_lexical_escape_refuses_at_load',
            'test_edi_external_data_dir_loads_and_roundtrips',
            ('absolute', 'parent'),
        ),
        (
            'test_edi_data_dir_symlink_escape_refuses_before_conversion_or_save',
            'test_edi_external_symlink_data_dir_allows_fit_and_save',
            ('fit', 'save'),
        ),
    )
    for argument in arguments
})
