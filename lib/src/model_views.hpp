// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <functional>
#include <map>
#include <memory>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include "edi/model.hpp"

// The Python-surface family hierarchies, mirroring crysta's pattern: a concrete class per
// implemented variant, factory-selected from the model's own type tags (factory-on-load), each a
// typed lens over the value-model storage the core (io/adapter/report) keeps using unchanged.
// Bindings-only: nothing in edi's C++ package surface moves. Adding a variant is ADDING A CLASS AND
// REGISTERING IT (model_views_registry.hpp is the registration surface).

namespace edi::views {

// ---- Peak ------------------------------------------------------------------------------------

// The abstract peak node (bound as "PeakBase"; the value struct edi::PeakBase stays the storage).
struct PeakNode {
    edi::ExperimentBase* experiment;
    explicit PeakNode(edi::ExperimentBase* experiment) : experiment(experiment) {}
    virtual ~PeakNode() = default;
    edi::PeakBase& storage() const { return experiment->peak; }
    std::vector<edi::Parameter*> parameters() const { return storage().parameters(); }
};

class PeakFactory {
   public:
    struct Row {
        std::function<std::unique_ptr<PeakNode>(edi::ExperimentBase*)> make;
    };
    static bool register_type(const std::string& token, Row row) {
        const bool inserted = table().emplace(token, std::move(row)).second;
        if (!inserted) {
            throw std::logic_error("duplicate peak-profile registration");
        }
        return true;
    }
    // The concrete peak over `experiment`, selected by its stored profile type (an absent tag is
    // the historical TOF-Jorgensen path, exactly the loader's rule). Fails closed on a profile
    // no class registered.
    static std::unique_ptr<PeakNode> make(edi::ExperimentBase* experiment) {
        const std::string type = experiment->peak.type.value_or(std::string("tof-jorgensen"));
        const auto& all = table();
        const auto found = all.find(type);
        if (found == all.end() || !found->second.make) {
            throw std::invalid_argument("this peak profile has no registered class");
        }
        return found->second.make(experiment);
    }

   private:
    static std::map<std::string, Row>& table() {
        static std::map<std::string, Row> rows;
        return rows;
    }
};

// ---- Instrument ------------------------------------------------------------------------------

struct InstrumentNode {
    edi::ExperimentBase* experiment;
    explicit InstrumentNode(edi::ExperimentBase* experiment) : experiment(experiment) {}
    virtual ~InstrumentNode() = default;
    edi::InstrumentBase& storage() const { return experiment->instrument; }
    std::vector<edi::Parameter*> parameters() const { return storage().parameters(); }
};

// Keyed by (beam mode, radiation probe): the CW family has a neutron and an X-ray instrument,
// and an experiment without a declared probe is neutron (effective_radiation_probe).
class InstrumentFactory {
   public:
    struct Row {
        std::function<std::unique_ptr<InstrumentNode>(edi::ExperimentBase*)> make;
    };
    using Key = std::pair<edi::BeamModeEnum, edi::RadiationProbeEnum>;
    static bool register_type(edi::BeamModeEnum mode, edi::RadiationProbeEnum probe, Row row) {
        const bool inserted = table().emplace(Key{mode, probe}, std::move(row)).second;
        if (!inserted) {
            throw std::logic_error("duplicate instrument registration");
        }
        return true;
    }
    static bool register_type(edi::BeamModeEnum mode, Row row) {
        return register_type(mode, edi::RadiationProbeEnum::NEUTRON, std::move(row));
    }
    static std::unique_ptr<InstrumentNode> make(edi::ExperimentBase* experiment) {
        const auto& all = table();
        const auto found = all.find(Key{experiment->effective_beam_mode(),
                                        experiment->experiment_type.effective_radiation_probe()});
        if (found == all.end() || !found->second.make) {
            throw std::invalid_argument(
                "this beam mode and radiation probe have no registered instrument class");
        }
        return found->second.make(experiment);
    }

   private:
    static std::map<Key, Row>& table() {
        static std::map<Key, Row> rows;
        return rows;
    }
};

// ---- Absorption ------------------------------------------------------------------------------

struct AbsorptionNode {
    edi::ExperimentBase* experiment;
    explicit AbsorptionNode(edi::ExperimentBase* experiment) : experiment(experiment) {}
    virtual ~AbsorptionNode() = default;
    edi::AbsorptionBase& storage() const { return experiment->absorption; }
    std::vector<edi::Parameter*> parameters() const { return storage().parameters(); }
};

class AbsorptionFactory {
   public:
    struct Row {
        std::function<std::unique_ptr<AbsorptionNode>(edi::ExperimentBase*)> make;
    };
    static bool register_type(const std::string& token, Row row) {
        const bool inserted = table().emplace(token, std::move(row)).second;
        if (!inserted) {
            throw std::logic_error("duplicate absorption-type registration: " + token);
        }
        return true;
    }
    // Token resolution mirrors the writer's own rule (io.cpp): an engaged `_absorption.type`
    // names the correction; otherwise an engaged ABSCOR pair is the cylinder correction and a
    // bare block is none. An engaged token no class registered fails closed, naming it.
    static std::unique_ptr<AbsorptionNode> make(edi::ExperimentBase* experiment) {
        const edi::AbsorptionBase& a = experiment->absorption;
        // An untyped block with an engaged mu_r body classifies as the Hewat cylinder, the CW
        // mirror of the ABSCOR-pair rule (canonical states always carry the type; this is the
        // hand-built-model fallback only).
        const std::string token =
            a.type ? *a.type
                   : ((a.abscor1 || a.abscor2) ? std::string("cylinder")
                      : a.mu_r                 ? std::string("cylinder-hewat")
                                               : std::string("none"));
        const auto& all = table();
        const auto found = all.find(token);
        if (found == all.end() || !found->second.make) {
            throw std::invalid_argument("absorption type '" + token +
                                        "' has no registered class");
        }
        return found->second.make(experiment);
    }

   private:
    static std::map<std::string, Row>& table() {
        static std::map<std::string, Row> rows;
        return rows;
    }
};

}  // namespace edi::views

