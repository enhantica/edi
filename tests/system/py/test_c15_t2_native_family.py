"""F1 native family admission; input declarations are the oracle."""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from tests.fixtures.c15_t2_polarization.family_projects import family_project

ROOT = Path(__file__).resolve().parents[3]
TERMS = ('setup_polarization_coefficient', 'setup_monochromator_twotheta')
ENDPOINTS = ('calculate', 'single-fit', 'joint-fit', 'save', 'delegated-save')
SOURCE = r"""#include "edi/model.hpp"
#include "edi/io.hpp"
#include <iostream>
#include <string>
int main(int argc, char** argv) {
    auto xray = edi::load_project(argv[1]);
    auto target = edi::load_project(argv[2]);
    const int term = std::stoi(argv[3]);
    const std::string state = argv[4], route = argv[5], endpoint = argv[6];
    try {
        auto& optional = term == 0 ? xray.experiment().instrument.setup_polarization_coefficient
                                  : xray.experiment().instrument.setup_monochromator_twotheta;
        optional->value = state == "value" ? (term == 0 ? 0.37 : 41.0) : 0.0;
        if (state == "free") optional->free = true;
        if (state == "declared") optional->uncertainty = 0.0;
        if (state == "start") optional->start_value = term == 0 ? 0.37 : 41.0;
        const bool metadata_route = route.find('-') != std::string::npos;
        auto& p = (route == "native" || route == "clean" || metadata_route) ? target : xray;
        if (metadata_route) {
            auto& slot = term == 0 ? p.experiment().instrument.setup_polarization_coefficient
                                   : p.experiment().instrument.setup_monochromator_twotheta;
            // Real public constructors: no loaded descriptor supplies the negative state.
            edi::Parameter incoming;
            incoming.uncertainty = state == "declared" ? std::optional<double>(0.0)
                                                       : std::nullopt;
            incoming.value = state == "value" ? (term == 0 ? 0.37 : 41.0) : 0.0;
            incoming.free = state == "free";
            if (state == "start") incoming.start_value = term == 0 ? 0.37 : 41.0;
            const auto& xi = xray.experiment().instrument;
            const auto& other = term == 0 ? xi.setup_monochromator_twotheta
                                         : xi.setup_polarization_coefficient;
            const bool mismatch = route.ends_with("mismatch");
            if (mismatch) incoming.spec = other->spec;
            if (route.starts_with("replace-")) {
                slot = optional;  // first engage with the loaded, correctly named parameter
                *slot = incoming; // then replace it with a detached native value
            } else if (route.starts_with("emplace-")) {
                slot.reset();
                slot.emplace(incoming.value.get(), incoming.uncertainty.get(),
                             incoming.free.get());
                slot->start_value = incoming.start_value.get();
                slot->spec = incoming.spec;
            } else {
                slot.reset();
                slot = incoming; // assign a separately constructed, descriptor-free value
            }
            if (!slot || (mismatch ? slot->spec != other->spec || !slot->spec
                                    : slot->spec != nullptr)) {
                throw std::runtime_error("VEHICLE metadata construction failed");
            }
            if (slot->value != incoming.value.get() || slot->free != incoming.free.get() ||
                slot->uncertainty.get() != incoming.uncertainty.get() ||
                slot->start_value.get() != incoming.start_value.get()) {
                throw std::runtime_error("VEHICLE numeric state construction failed");
            }
            // A real fit request also needs a legal free column unrelated to polarization.
            if (endpoint == "single-fit" || endpoint == "joint-fit")
                p.experiment().linked_structure().scale.free = true;
            std::cout << "VEHICLE " << route << '\n' << std::flush;
        } else if (route == "native") {
            auto& e = target.experiment();
            e.instrument.setup_polarization_coefficient =
                xray.experiment().instrument.setup_polarization_coefficient;
            e.instrument.setup_monochromator_twotheta =
                xray.experiment().instrument.setup_monochromator_twotheta;


        } else if (route == "retag") {
            auto& e = p.experiment(); const auto& t = target.experiment();
            e.experiment_type.radiation_probe = edi::RadiationProbeEnum::NEUTRON;
            e.xray_form_factor.reset(); e.xray_dispersion.reset();
            if (t.experiment_type.effective_beam_mode() == edi::BeamModeEnum::TIME_OF_FLIGHT) {
                auto k = e.instrument.setup_polarization_coefficient;
                auto a = e.instrument.setup_monochromator_twotheta;
                e.experiment_type.beam_mode = edi::BeamModeEnum::TIME_OF_FLIGHT;
                e.peak = t.peak; e.instrument = t.instrument; e.data = t.data;
                e.instrument.setup_polarization_coefficient = k;
                e.instrument.setup_monochromator_twotheta = a;
            }
        }
        if (endpoint == "calculate") p.calculate();
        else if (endpoint == "single-fit") (void)p.fit();
        else if (endpoint == "joint-fit") { p.fitting_mode = "joint"; (void)p.fit_joint(); }
        else if (endpoint == "save") edi::save_project(p, argv[7]);
        else if (endpoint == "delegated-save") edi::save_project_via_crysta(p, argv[7]);
        std::cout << "ADMITTED\n";
    } catch (const std::exception& e) { std::cout << "REFUSED " << e.what() << '\n'; }
}
"""


@pytest.fixture(scope='module')
def native_family_probe(tmp_path_factory):
    directory = tmp_path_factory.mktemp('-family-native')
    source = directory / 'consumer.cpp'
    source.write_text(SOURCE)
    binary = directory / 'consumer'
    sdk = Path(os.environ.get('CRYSTA_SDK_DIR', ROOT / 'build/crysta-prefix'))
    build = ROOT / ('build/ci-consumer' if os.environ.get('CRYSTA_SDK_DIR') else 'build/ci')
    environment = Path(sys.executable).resolve().parent.parent
    compiler = shutil.which('clang++')
    assert compiler, ' F1 the native gate requires the pinned Clang compiler'
    flags = [
        compiler,
        '-std=c++20',
        '-pthread',
        '-I' + str(ROOT / 'core/include'),
        '-I' + str(sdk / 'include'),
        '-I' + str(environment / 'include/eigen3'),
    ]
    libraries = [str(build / 'core/libedi_core.a'), str(sdk / 'lib/libcrysta_core.a')]
    libraries += ['-lgomp'] if sys.platform == 'linux' else ['-lomp']
    environment_lib = Path(sys.executable).resolve().parent.parent / 'lib'
    compiled = subprocess.run(
        [
            *flags,
            '-O0',
            str(source),
            *libraries,
            '-L' + str(environment_lib),
            '-Wl,-rpath,' + str(environment_lib),
            '-lsleef',
            '-o',
            str(binary),
        ],
        text=True,
        capture_output=True,
        check=False,
        timeout=25,
    )
    assert compiled.returncode == 0, (
        ' F1 native escape vehicle must compile before testing admission: ' + compiled.stderr
    )
    xray = family_project(directory / 'xray', 'xray')
    families = {
        family: family_project(directory / family, family) for family in ('neutron-cw', 'tof')
    }
    families['xray'] = xray
    return binary, xray, families


def _run(native_family_probe, tmp_path, term, state, route, family, endpoint):
    binary, xray, families = native_family_probe
    result = subprocess.run(
        [
            str(binary),
            str(xray),
            str(families[family]),
            str(TERMS.index(term)),
            state,
            route,
            endpoint,
            str(tmp_path / 'saved'),
        ],
        text=True,
        capture_output=True,
        check=False,
        timeout=10,
    )
    assert result.returncode == 0, (
        ' F1 native admission must report a refusal or success without crashing: ' + result.stderr
    )
    return result.stdout


METADATA_ROUTES = tuple(
    f'{construction}-{metadata}'
    for construction in ('assign', 'replace', 'emplace')
    for metadata in ('bare', 'mismatch')
)


@pytest.mark.parametrize('term', TERMS)
@pytest.mark.parametrize('state', ['value', 'free', 'declared', 'start'])
@pytest.mark.parametrize('route', METADATA_ROUTES)
@pytest.mark.parametrize('family', ['neutron-cw', 'tof'])
@pytest.mark.parametrize('endpoint', ENDPOINTS)
def test_native_metadata_refusal_names_storage_member(
    native_family_probe, tmp_path, term, state, route, family, endpoint
):
    output = _run(native_family_probe, tmp_path, term, state, route, family, endpoint)
    assert output.startswith(f'VEHICLE {route}\nREFUSED '), (
        ' F1 native bare or mismatched metadata must reach a safe family refusal: ' + output
    )
    other = TERMS[1 - TERMS.index(term)]
    assert f'_instrument.{term}' in output and other not in output, (
        ' F1 family refusal must name the actual optional storage member independently '
        'of null or caller-controlled descriptor identity: ' + output
    )


@pytest.mark.parametrize('term', TERMS)
@pytest.mark.parametrize('route', METADATA_ROUTES)
@pytest.mark.parametrize('family', ['neutron-cw', 'tof'])
@pytest.mark.parametrize('endpoint', ENDPOINTS)
def test_native_metadata_inert_default_is_admitted(
    native_family_probe, tmp_path, term, route, family, endpoint
):
    output = _run(native_family_probe, tmp_path, term, 'inert', route, family, endpoint)
    assert output.startswith(f'VEHICLE {route}\nADMITTED'), (
        ' F1 an engaged zero, fixed parameter without uncertainty or fit start stays '
        'inert on valid neutron CW and TOF consumers even with bare or mismatched metadata: '
        + output
    )


@pytest.mark.parametrize('term', TERMS)
@pytest.mark.parametrize('route', METADATA_ROUTES)
@pytest.mark.parametrize('endpoint', ['calculate', 'save', 'delegated-save'])
def test_native_metadata_valid_xray_is_admitted(
    native_family_probe, tmp_path, term, route, endpoint
):
    output = _run(native_family_probe, tmp_path, term, 'value', route, 'xray', endpoint)
    assert output.startswith(f'VEHICLE {route}\nADMITTED'), (
        ' F1 valid nonidentity X-ray state must reach calculation and both save '
        'consumers independently of incoming descriptor metadata: ' + output
    )


@pytest.mark.parametrize('term', TERMS)
@pytest.mark.parametrize('state', ['value', 'free', 'declared', 'start'])
@pytest.mark.parametrize('route', ['native', 'retag'])
@pytest.mark.parametrize('family', ['neutron-cw', 'tof'])
@pytest.mark.parametrize('endpoint', ENDPOINTS)
def test_native_foreign_family_never_discards_polarization(
    native_family_probe,
    tmp_path,
    term,
    state,
    route,
    family,
    endpoint,
):
    output = _run(native_family_probe, tmp_path, term, state, route, family, endpoint)
    named = any(name in output for name in TERMS)
    layout = 'instrument holds' in output and 'dictionary layout declares' in output
    assert output.startswith('REFUSED ') and (named or layout), (
        ' F1 unsupported-family declared, nondefault, free or fit-start polarization '
        'must refuse by parameter name before calculation, fitting or save: ' + output
    )


@pytest.mark.parametrize('endpoint', ['calculate', 'save'])
def test_native_valid_xray_control_reaches_real_consumption(
    native_family_probe,
    tmp_path,
    endpoint,
):
    output = _run(
        native_family_probe, tmp_path, TERMS[0], 'value', 'valid', 'neutron-cw', endpoint
    )
    assert output.startswith('ADMITTED'), (
        ' F1 family gate must admit the valid nonidentity X-ray calculation and save: ' + output
    )


@pytest.mark.parametrize('family', ['neutron-cw', 'tof'])
@pytest.mark.parametrize('endpoint', ['calculate', 'save'])
def test_native_unsupported_family_without_polarization_is_valid(
    native_family_probe,
    tmp_path,
    family,
    endpoint,
):
    output = _run(native_family_probe, tmp_path, TERMS[0], 'value', 'clean', family, endpoint)
    assert output.startswith('ADMITTED'), (
        ' F1 negative vehicles must be valid neutron CW and TOF models before engagement: '
        + output
    )
