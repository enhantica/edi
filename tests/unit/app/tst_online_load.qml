// SPDX-License-Identifier: BSD-3-Clause
OnlineLoadCase {
    name: "OnlineLoad"

    function test_new_experiment_wavelength() { check_new_experiment_wavelength(); }
    function test_actions_and_formats_data() { return check_actions_and_formats_data(); }
    function test_actions_and_formats(data) { check_actions_and_formats(data); }
    function test_from_web_opens_source_selector_data() { return check_from_web_opens_source_selector_data(); }
    function test_from_web_opens_source_selector(data) { check_from_web_opens_source_selector(data); }
}
