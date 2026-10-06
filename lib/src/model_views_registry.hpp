// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include "model_views.hpp"

// The REGISTRATION SURFACE: every concrete family class registers itself below. Adding a variant = its
// class + its registration here (plus the enum member, when the wire vocabulary grows with the feature).
// Nothing else changes.

namespace edi::views {

// ---- Peak concretes --------------------------------------------------------------------------

struct TofJorgensen : PeakNode {
    using PeakNode::PeakNode;
    const char* profile() const override { return "tof-jorgensen"; }
};

struct TofJorgensenVonDreele final : TofJorgensen {
    using TofJorgensen::TofJorgensen;
    const char* profile() const override { return "tof-jorgensen-von-dreele"; }
};

// The constant-wavelength profiles and the TOF pseudo-Voigt.
struct CwlGaussian final : PeakNode {
    using PeakNode::PeakNode;
    const char* profile() const override { return "cwl-gaussian"; }
};

struct CwlLorentzian final : PeakNode {
    using PeakNode::PeakNode;
    const char* profile() const override { return "cwl-lorentzian"; }
};

struct CwlPseudoVoigt final : PeakNode {
    using PeakNode::PeakNode;
    const char* profile() const override { return "cwl-pseudo-voigt"; }
};

struct CwlPseudoVoigtBerarBaldinozzi final : PeakNode {
    using PeakNode::PeakNode;
    const char* profile() const override { return "cwl-pseudo-voigt-berar-baldinozzi"; }
};

struct CwlTchPseudoVoigt final : PeakNode {
    using PeakNode::PeakNode;
    const char* profile() const override { return "cwl-tch-pseudo-voigt"; }
};

struct CwlTchPseudoVoigtFcj final : PeakNode {
    using PeakNode::PeakNode;
    const char* profile() const override { return "cwl-tch-pseudo-voigt-fcj"; }
};

struct TofPseudoVoigt final : PeakNode {
    using PeakNode::PeakNode;
    const char* profile() const override { return "tof-pseudo-voigt"; }
};

inline const bool tof_jorgensen_registered = PeakFactory::register_type(
    "tof-jorgensen",
    {[](edi::ExperimentBase* experiment) -> std::unique_ptr<PeakNode> {
        return std::make_unique<TofJorgensen>(experiment);
    }});

inline const bool tof_jorgensen_von_dreele_registered = PeakFactory::register_type(
    "tof-jorgensen-von-dreele",
    {[](edi::ExperimentBase* experiment) -> std::unique_ptr<PeakNode> {
        return std::make_unique<TofJorgensenVonDreele>(experiment);
    }});

inline const bool cwl_gaussian_registered = PeakFactory::register_type(
    "cwl-gaussian",
    {[](edi::ExperimentBase* experiment) -> std::unique_ptr<PeakNode> {
        return std::make_unique<CwlGaussian>(experiment);
    }});

inline const bool cwl_lorentzian_registered = PeakFactory::register_type(
    "cwl-lorentzian",
    {[](edi::ExperimentBase* experiment) -> std::unique_ptr<PeakNode> {
        return std::make_unique<CwlLorentzian>(experiment);
    }});

inline const bool cwl_pseudo_voigt_registered = PeakFactory::register_type(
    "cwl-pseudo-voigt",
    {[](edi::ExperimentBase* experiment) -> std::unique_ptr<PeakNode> {
        return std::make_unique<CwlPseudoVoigt>(experiment);
    }});

inline const bool cwl_pseudo_voigt_berar_baldinozzi_registered = PeakFactory::register_type(
    "cwl-pseudo-voigt-berar-baldinozzi",
    {[](edi::ExperimentBase* experiment) -> std::unique_ptr<PeakNode> {
        return std::make_unique<CwlPseudoVoigtBerarBaldinozzi>(experiment);
    }});

inline const bool cwl_tch_pseudo_voigt_registered = PeakFactory::register_type(
    "cwl-tch-pseudo-voigt",
    {[](edi::ExperimentBase* experiment) -> std::unique_ptr<PeakNode> {
        return std::make_unique<CwlTchPseudoVoigt>(experiment);
    }});

inline const bool cwl_tch_pseudo_voigt_fcj_registered = PeakFactory::register_type(
    "cwl-tch-pseudo-voigt-fcj",
    {[](edi::ExperimentBase* experiment) -> std::unique_ptr<PeakNode> {
        return std::make_unique<CwlTchPseudoVoigtFcj>(experiment);
    }});

inline const bool tof_pseudo_voigt_registered = PeakFactory::register_type(
    "tof-pseudo-voigt",
    {[](edi::ExperimentBase* experiment) -> std::unique_ptr<PeakNode> {
        return std::make_unique<TofPseudoVoigt>(experiment);
    }});

// ---- Instrument concretes --------------------------------------------------------------------

struct TofPdInstrument final : InstrumentNode {
    using InstrumentNode::InstrumentNode;
};

// The abstract CWL chain intermediates: present in the hierarchy, never constructible from Python (no
// bound init).
struct CwlInstrumentBase : InstrumentNode {
    using InstrumentNode::InstrumentNode;
};

struct CwlPdInstrumentBase : CwlInstrumentBase {
    using CwlInstrumentBase::CwlInstrumentBase;
};

struct CwlPdNeutronInstrument final : CwlPdInstrumentBase {
    using CwlPdInstrumentBase::CwlPdInstrumentBase;
};

// The CW X-ray instrument (diffraction-lib `cwl-pd-xray`) — the same two CW slots; the
// experiment's radiation selects crysta's X-ray f0 amplitudes. Polarization members.
struct CwlPdXrayInstrument final : CwlPdInstrumentBase {
    using CwlPdInstrumentBase::CwlPdInstrumentBase;
};

inline const bool tof_pd_instrument_registered = InstrumentFactory::register_type(
    edi::BeamModeEnum::TIME_OF_FLIGHT,
    {[](edi::ExperimentBase* experiment) -> std::unique_ptr<InstrumentNode> {
        return std::make_unique<TofPdInstrument>(experiment);
    }});

inline const bool cwl_pd_neutron_instrument_registered = InstrumentFactory::register_type(
    edi::BeamModeEnum::CONSTANT_WAVELENGTH,
    {[](edi::ExperimentBase* experiment) -> std::unique_ptr<InstrumentNode> {
        return std::make_unique<CwlPdNeutronInstrument>(experiment);
    }});

inline const bool cwl_pd_xray_instrument_registered = InstrumentFactory::register_type(
    edi::BeamModeEnum::CONSTANT_WAVELENGTH, edi::RadiationProbeEnum::XRAY,
    {[](edi::ExperimentBase* experiment) -> std::unique_ptr<InstrumentNode> {
        return std::make_unique<CwlPdXrayInstrument>(experiment);
    }});

// ---- Absorption concretes --------------------------------------------------------------------

struct CylinderHewatAbsorption final : AbsorptionNode {
    using AbsorptionNode::AbsorptionNode;
};

// The Lobanov fit's own concrete — CW-only, carrying the same mu_r body through the shared
// AbsorptionNode storage.
struct CylinderLobanovAbsorption final : AbsorptionNode {
    using AbsorptionNode::AbsorptionNode;
};

struct NoAbsorption final : AbsorptionNode {
    using AbsorptionNode::AbsorptionNode;
};

inline const bool cylinder_hewat_absorption_registered = AbsorptionFactory::register_type(
    "cylinder", {[](edi::ExperimentBase* experiment) -> std::unique_ptr<AbsorptionNode> {
        return std::make_unique<CylinderHewatAbsorption>(experiment);
    }});

// Every built-in selector token the loader accepts resolves here too — the CW
// "cylinder-hewat" file token maps to the same Hewat concrete as the TOF "cylinder"
// spelling (one lens, two file tokens), and "cylinder-lobanov" constructs its own concrete.
inline const bool cylinder_hewat_cw_absorption_registered = AbsorptionFactory::register_type(
    "cylinder-hewat", {[](edi::ExperimentBase* experiment) -> std::unique_ptr<AbsorptionNode> {
        return std::make_unique<CylinderHewatAbsorption>(experiment);
    }});

inline const bool cylinder_lobanov_absorption_registered = AbsorptionFactory::register_type(
    "cylinder-lobanov", {[](edi::ExperimentBase* experiment) -> std::unique_ptr<AbsorptionNode> {
        return std::make_unique<CylinderLobanovAbsorption>(experiment);
    }});

inline const bool no_absorption_registered = AbsorptionFactory::register_type(
    "none", {[](edi::ExperimentBase* experiment) -> std::unique_ptr<AbsorptionNode> {
        return std::make_unique<NoAbsorption>(experiment);
    }});

}  // namespace edi::views
