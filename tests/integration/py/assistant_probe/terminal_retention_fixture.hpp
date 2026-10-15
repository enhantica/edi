// Tests-owned retaining-role witness for the exact accepted e0a1a7799 interface.
#pragma once
#include "edi/assistant.hpp"
#include "json.hpp"
#include <thread>
#include <stdexcept>

struct IndependentRetention {
    using Value=edi::json::Value;
    using Array=edi::json::Array;
    using Object=edi::json::Object;
    std::string mode;
    std::thread::id owner=std::this_thread::get_id();
    Array prospective,terminals,trace,archive;
    unsigned started=0,settled=0,quarantined=0,destroyed=0,violations=0,held=0;
    explicit IndependentRetention(std::string policy):mode(std::move(policy)) {}
    void record(const char* action) noexcept {
        if(std::this_thread::get_id()!=owner) ++violations;
        try {trace.emplace_back(action);} catch(...) {++violations;}
    }
    struct Lease final:edi::assistant::TerminalRetention {
        IndependentRetention& role;
        bool released=false;
        Value pending;
        Lease(IndependentRetention& owner,Value row):role(owner),pending(std::move(row)) {++role.held;}
        ~Lease() noexcept override {role.record("destroy");++role.destroyed;if(!released)--role.held;}
        bool started() noexcept override {
            role.record("started");++role.started;
            if(role.mode=="started-false")return false;
            try {role.archive.push_back(pending);return true;} catch(...) {return false;}
        }
        bool settle(const std::string& terminal) noexcept override {
            role.record("settle");++role.settled;
            try {
                role.terminals.push_back(edi::json::parse(terminal));
                if(role.mode=="settle-false")return false;
                role.archive.push_back(Object{{"kind","terminal"},{"payload",edi::json::parse(terminal)}});
                --role.held;released=true;return true;
            }catch(...) {return false;}
        }
        void quarantine() noexcept override {role.record("quarantine");++role.quarantined;}
    };
    std::unique_ptr<edi::assistant::TerminalRetention> reserve(const std::string& text) {
        record("reserve");prospective.push_back(edi::json::parse(text));
        if(mode=="throw")throw std::runtime_error("synthetic-sensitive-reservation-body");
        if(mode=="null")return {};
        auto row=Object{{"kind","activity"},{"prospective",edi::json::parse(text)}};
        return std::make_unique<Lease>(*this,Value(row));
    }
    Value observation() const {
        return Object{{"prospective",prospective},{"terminals",terminals},{"archive",archive},
            {"trace",trace},{"started",static_cast<int>(started)},{"settled",static_cast<int>(settled)},
            {"quarantined",static_cast<int>(quarantined)},{"destroyed",static_cast<int>(destroyed)},
            {"held",static_cast<int>(held)},{"owner_violations",static_cast<int>(violations)}};
    }
};
