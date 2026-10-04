#include <doctest/doctest.h>
#include <atomic>
#include <fstream>
#include <cmath>
#include <condition_variable>
#include <mutex>
#include <optional>
#include <thread>
#include "edi/io.hpp"
#include "edi/calculation.hpp"
#include "edi/parameter_walk.hpp"
#include "edi/presentation.hpp"
#include "e04_t9_support.hpp"

#if __has_include("edi/fit_job.hpp")
#include "edi/fit_job.hpp"
#define E05_T1_FIT_JOB 1
#else
#define E05_T1_FIT_JOB 0
#endif

namespace e05_t1 {
// ADL keeps the absent-feature baseline executable; no fallback can supply a read-out.
template<class Source, class Series>
std::string readout(const Source& source, const Series& series) {
    if constexpr (requires { hover_readout(source, series, std::size_t{0}); }) {
        std::string text;
        for(const auto& line:hover_readout(source,series,0)) text+=line.text+"\n";
        return text;
    }
    return {};
}

#if E05_T1_FIT_JOB
// Input reduction only: no expected fit number comes from this generator.
edi::Project small(const std::string& mode = "single") {
    edi::Project p;
    auto& structure=p.structure();structure.name="silicon";
    structure.space_group.name_h_m="P 1";
    structure.cell.length_a.value=structure.cell.length_b.value=structure.cell.length_c.value=3.0;
    auto atom=std::make_shared<edi::AtomSite>();atom->id="Si1";atom->type_symbol="Si";atom->wyckoff_letter="a";
    atom->fract_x.value=.23;atom->fract_y.value=.31;atom->fract_z.value=.41;
    structure.atom_sites.push_back(atom);
    auto& experiment=p.experiment();experiment.name="first";
    experiment.linked_structure.structure_id="silicon";
    experiment.linked_structure.scale.value=1.0;
    experiment.instrument.setup_wavelength.emplace();
    experiment.instrument.setup_wavelength->value=1.54;
    experiment.peak.type="cwl-pseudo-voigt";
    experiment.peak.broad_gauss_u.emplace(); experiment.peak.broad_gauss_u->value=0;
    experiment.peak.broad_gauss_v.emplace(); experiment.peak.broad_gauss_v->value=0;
    experiment.peak.broad_lorentz_x.emplace(); experiment.peak.broad_lorentz_x->value=0;
    experiment.peak.broad_lorentz_y.emplace(); experiment.peak.broad_lorentz_y->value=.001;
    experiment.instrument.calib_twotheta_offset.emplace(); experiment.instrument.calib_twotheta_offset->value=0;
    experiment.peak.broad_gauss_w.emplace();
    experiment.peak.broad_gauss_w->value=.08;
    experiment.data.emplace();
    std::vector<double> x,y,su;
    for(int i=0;i<24;++i) {x.push_back(20.0+3*i);y.push_back(1);su.push_back(1);}
    experiment.data->write_axis(&edi::PdDataBase::two_theta,std::move(x));
    experiment.data->write_column(&edi::PdDataBase::intensity_meas,std::move(y));
    experiment.data->write_column(&edi::PdDataBase::intensity_meas_su,std::move(su));
    p.calculate();
    // Calculated values generate the input only, never the correctness expectation.
    auto measured=edi::capture_pattern(p,0).calc;
    std::vector<double> observed;
    for(double value:*measured) observed.push_back(1.73*value+.25);
    experiment.data->write_column(&edi::PdDataBase::intensity_meas,std::move(observed));
    for(auto& entry:edi::parameter_entries(p)) entry.parameter->free=false;
    experiment.linked_structure.scale.free=true;
    p.calculate();
    p.minimizer_max_iterations = 4;
    p.minimizer_chi_square_tolerance = 1e-12;
    p.fitting_mode = mode;
    if (mode == "joint") {
        auto second = std::make_shared<edi::BraggPdExperiment>(p.experiment());
        second->name = "second";
        second->linked_structure.scale.value *= 1.37;
        p.experiments.push_back(second);
        p.calculate();
    }
    return p;
}
struct Trace {
    std::mutex mutex;
    std::condition_variable condition;
    std::vector<edi::work::Event> events;
    void add(const edi::work::Event& event) {
        std::lock_guard lock(mutex); events.push_back(event); condition.notify_all();
    }
    void finished() {
        std::unique_lock lock(mutex);
        REQUIRE_MESSAGE((condition.wait_for(lock, std::chrono::seconds(10), [&] {
            return std::any_of(events.begin(), events.end(), [](const auto& e) { return e.kind == edi::work::EventKind::Finished; });
        })), " gate 2 worker finishes under trace control without sleeping");
    }
};
bool near(double a, double b) { return std::abs(a-b) <= std::max(5e-10, 5e-9*std::abs(b)); }
void compare_result(const edi::FitResultBase& actual, const edi::FitResultBase& expected) {
    CHECK_MESSAGE((actual.status == expected.status), " gate 1 status equals independent synchronous core fit");
    CHECK_MESSAGE((actual.iterations == expected.iterations), " gate 2 accepted step count equals independent core fit");
    CHECK_MESSAGE((near(actual.reduced_chi_square, expected.reduced_chi_square)), " gate 1 chi-square uses existing CLI parity tolerance");
    REQUIRE_MESSAGE((actual.values.size() == expected.values.size()), " gate 1 fitted identity set is exact");
    REQUIRE_MESSAGE((actual.uncertainty.size() == expected.uncertainty.size()), " gate 1 fitted uncertainty identity set is exact");
    for (const auto& [key, value] : expected.values) {
        REQUIRE_MESSAGE((actual.values.contains(key)), " gate 1 every reference fitted identity exists");
        CHECK_MESSAGE((near(actual.values.at(key), value)), " gate 1 every fitted value equals independent core fit");
    }
    for (const auto& [key, value] : expected.uncertainty) {
        REQUIRE_MESSAGE((actual.uncertainty.contains(key)), " gate 1 every reference e.s.d. identity exists");
        CHECK_MESSAGE((near(actual.uncertainty.at(key), value)), " gate 1 every e.s.d. equals independent core fit");
    }
}
void consistency(edi::Project& p, const edi::FitResultBase& result) {
    for (const auto& entry : edi::parameter_entries(p)) if (result.values.contains(entry.path)) {
        CHECK_MESSAGE((near(entry.parameter->value, result.values.at(entry.path))), " gate 4 final values and table use the same fit result");
        CHECK_MESSAGE((near(entry.parameter->uncertainty.get().value_or(0.0), result.uncertainty.at(entry.path))), " gate 4 final errors and table use the same fit result");
    }
    auto fresh = edi::snapshot_for_work(p).project; fresh.calculate();
    for (std::size_t bank=0; bank<p.experiments.size(); ++bank) {
        const auto live = edi::capture_pattern(p, bank), control = edi::capture_pattern(fresh, bank);
        REQUIRE_MESSAGE((live.current && live.calc && control.calc), " gate 4 final calculated category is current in every bank");
        REQUIRE_MESSAGE((live.calc->size() == control.calc->size()), " gate 4 fresh and final grids have identical cardinality");
        for (std::size_t i=0; i<live.calc->size(); ++i)
            CHECK_MESSAGE(((near((*live.calc)[i], (*control.calc)[i]) || (std::isnan((*live.calc)[i]) && std::isnan((*control.calc)[i])))),
                          " gate 4 final Icalc equals fresh calculation at fitted state including excluded gaps");
    }
}
#endif
}

TEST_CASE("E05-T1 gates 1 2 4 single and joint fit streams preserve all deliveries") {
#if E05_T1_FIT_JOB
    for (const auto& mode : {"single", "joint"}) {
        INFO(mode);
        auto live = e05_t1::small(mode);
        auto reference = edi::snapshot_for_work(live).project;
        const auto expected = mode == std::string("joint") ? reference.fit_joint() : reference.fit();
        e04_t9::OwnerQueue queue; e05_t1::Trace trace;
        const auto owner = std::this_thread::get_id();
        edi::work::Worker worker([&](auto d) { queue.post(std::move(d)); }, {{}, [&](const auto& e) { trace.add(e); }});
        std::vector<edi::IterationRecord> progress;
        std::optional<edi::FitReport> final;
        int preambles=0, finishes=0;
        edi::FitJob fit(live, worker, {
            [&](const auto& start) {
                CHECK_MESSAGE((std::this_thread::get_id()==owner), " gate 2 preamble arrives on owner thread");
                CHECK_MESSAGE((progress.empty() && !final), " gate 2 pre-fit record arrives before all accepted iterations");
                CHECK_MESSAGE((start.pre_fit.iteration==0), " gate 2 preamble starts at iteration zero");
                CHECK_MESSAGE((e05_t1::near(start.pre_fit.reduced_chi_square, expected.pre_fit.reduced_chi_square)), " gate 2 pre-fit chi-square equals independent core preamble");
                ++preambles;
            },
            [&](const auto& record) {
                CHECK_MESSAGE((std::this_thread::get_id()==owner), " gate 2 accepted iterations arrive on owner thread");
                CHECK_MESSAGE((preambles==1 && !final), " gate 2 each iteration is between sole preamble and final delivery");
                progress.push_back(record);
            },
            {}, [&](const auto& result) {
                CHECK_MESSAGE((std::this_thread::get_id()==owner), " gate 4 atomic final write-back arrives on owner thread");
                final=result; ++finishes;
                CHECK_MESSAGE((result.refusal.empty()), " gate 5 valid single and joint inputs are not refused");
                REQUIRE_MESSAGE((result.result.has_value()), " gate 4 accepted final report carries its complete fit result");
                e05_t1::consistency(live, *result.result);
            }});
        fit.start();
        while (!final) queue.one();
        trace.finished(); queue.drain();
        REQUIRE_MESSAGE((final.has_value()), " gate 2 a fit has a final delivery");
        CHECK_MESSAGE((preambles==1 && finishes==1 && !fit.running()), " gate 2 no duplicate or post-final delivery remains");
        e05_t1::compare_result(*final->result, expected);
        REQUIRE_MESSAGE((progress.size()==final->result->iterations_history.size() && !progress.empty()), " gate 2 all accepted iterations arrive exactly once and nonvacuously");
        for (std::size_t i=0; i<progress.size(); ++i) {
            const auto& r=final->result->iterations_history[i];
            CHECK_MESSAGE((progress[i].iteration==r.iteration && e05_t1::near(progress[i].rwp,r.rwp) && e05_t1::near(progress[i].reduced_chi_square,r.reduced_chi_square)), " gate 2 progress order and values equal complete accepted-step history");
        }
        std::lock_guard lock(trace.mutex);
        for (const auto& e : trace.events) {
            if (e.kind==edi::work::EventKind::Delivered) CHECK_MESSAGE((e.thread==owner), " gate 2 worker trace proves owner-thread delivery");
            if (e.kind==edi::work::EventKind::Started) CHECK_MESSAGE((e.thread!=owner), " gate 7 worker trace proves fit never runs on GUI thread");
        }
    }
#else
    FAIL_CHECK(" gates 1 2 4 require the packet's core FitJob ordered fit stream");
#endif
}

TEST_CASE("E05-T1 gate 3 engine checkpoint cancel retains partial values and undo") {
#if E05_T1_FIT_JOB
    const auto mode="single";
    INFO(mode);
    auto live=e05_t1::small(mode); const auto before=edi::project_edi_files(live);
    auto reference=edi::snapshot_for_work(live).project;
    int reference_checks=0;
    const auto cancel=[&] { return ++reference_checks==3; };
    const auto expected=mode==std::string("joint")?reference.fit_joint({}, {},cancel):reference.fit({}, {},cancel);
    e04_t9::OwnerQueue queue; edi::work::Worker worker([&](auto d) { queue.post(std::move(d)); });
    std::optional<edi::FitReport> final; int checks=0, finishes=0;
    e04_t9::Barrier first_poll; std::atomic<edi::work::Ticket> ticket{0};
    edi::FitJob fit(live,worker,{{},{},{},[&](const auto& r){final=r;++finishes;}}, {[&](int poll){
        checks=poll; if(poll==1) first_poll.block(); if(poll==3) worker.cancel(ticket.load());
    }});
    fit.start(); ticket=fit.ticket(); first_poll.entered(); first_poll.release();
    while(!final) queue.one(); queue.drain();
    REQUIRE_MESSAGE((final->result.has_value()), " gate 3 cancelled final report retains the engine partial result");
    CHECK_MESSAGE((final->result->status==edi::FitStatus::CANCELLED), " gate 3 counter seam cancels at the engine's next check");
    CHECK_MESSAGE((checks==reference_checks && finishes==1), " gate 3 cancel checkpoint and final-delivery counts are exact");
    e05_t1::compare_result(*final->result,expected); e05_t1::consistency(live,*final->result);
    edi::undo_fit(live); live.calculate();
    CHECK_MESSAGE((edi::project_edi_files(live)==before), " gate 3 undo restores every saved pre-fit byte after partial cancel");
#else
    FAIL_CHECK(" gate 3 requires the core FitJob cancellation and partial-result path");
#endif
}

TEST_CASE("E05-T1 gate 3 joint engine checkpoint cancel retains partial values and undo") {
#if E05_T1_FIT_JOB
    const auto mode="joint";
    INFO(mode);
    auto live=e05_t1::small(mode); const auto before=edi::project_edi_files(live);
    auto reference=edi::snapshot_for_work(live).project;
    int reference_checks=0;
    const auto cancel=[&] { return ++reference_checks==3; };
    const auto expected=mode==std::string("joint")?reference.fit_joint({}, {},cancel):reference.fit({}, {},cancel);
    e04_t9::OwnerQueue queue; edi::work::Worker worker([&](auto d) { queue.post(std::move(d)); });
    std::optional<edi::FitReport> final; int checks=0, finishes=0;
    e04_t9::Barrier first_poll; std::atomic<edi::work::Ticket> ticket{0};
    edi::FitJob fit(live,worker,{{},{},{},[&](const auto& r){final=r;++finishes;}}, {[&](int poll){
        checks=poll; if(poll==1) first_poll.block(); if(poll==3) worker.cancel(ticket.load());
    }});
    fit.start(); ticket=fit.ticket(); first_poll.entered(); first_poll.release();
    while(!final) queue.one(); queue.drain();
    REQUIRE_MESSAGE((final->result.has_value()), " gate 3 cancelled final report retains the engine partial result");
    CHECK_MESSAGE((final->result->status==edi::FitStatus::CANCELLED), " gate 3 counter seam cancels at the engine's next check");
    CHECK_MESSAGE((checks==reference_checks && finishes==1), " gate 3 cancel checkpoint and final-delivery counts are exact");
    e05_t1::compare_result(*final->result,expected); e05_t1::consistency(live,*final->result);
    edi::undo_fit(live); live.calculate();
    CHECK_MESSAGE((edi::project_edi_files(live)==before), " gate 3 undo restores every saved pre-fit byte after partial cancel");
#else
    FAIL_CHECK(" gate 3 requires the core FitJob cancellation and partial-result path");
#endif
}

TEST_CASE("E05-T1 gate 3 worker token cancellation reaches a running fit") {
#if E05_T1_FIT_JOB
    const auto mode="single";
    INFO(mode);
    auto live=e05_t1::small(mode); e04_t9::OwnerQueue queue; e04_t9::Barrier checkpoint;
    edi::work::Worker worker([&](auto d){queue.post(std::move(d));});
    std::optional<edi::FitReport> final;
    edi::FitJob fit(live,worker,{{},{},{},[&](const auto& r){final=r;}}, {[&](int poll){if(poll==1) checkpoint.block();}});
    fit.start(); checkpoint.entered(); fit.cancel(); checkpoint.release();
    while(!final) queue.one(); queue.drain();
    REQUIRE_MESSAGE((final->result.has_value()), " gate 3 cancelled final report retains the engine partial result");
    CHECK_MESSAGE((final->result->status==edi::FitStatus::CANCELLED && !fit.running()), " gate 3 actual worker token is polled after cancellation during the job");
#else
    FAIL_CHECK(" gate 3 requires the core FitJob to read its Worker's cancellation token");
#endif
}

TEST_CASE("E05-T1 gate 3 joint worker token cancellation reaches a running fit") {
#if E05_T1_FIT_JOB
    const auto mode="joint";
    INFO(mode);
    auto live=e05_t1::small(mode); e04_t9::OwnerQueue queue; e04_t9::Barrier checkpoint;
    edi::work::Worker worker([&](auto d){queue.post(std::move(d));});
    std::optional<edi::FitReport> final;
    edi::FitJob fit(live,worker,{{},{},{},[&](const auto& r){final=r;}}, {[&](int poll){if(poll==1) checkpoint.block();}});
    fit.start(); checkpoint.entered(); fit.cancel(); checkpoint.release();
    while(!final) queue.one(); queue.drain();
    REQUIRE_MESSAGE((final->result.has_value()), " gate 3 cancelled final report retains the engine partial result");
    CHECK_MESSAGE((final->result->status==edi::FitStatus::CANCELLED && !fit.running()), " gate 3 actual worker token is polled after cancellation during the job");
#else
    FAIL_CHECK(" gate 3 requires the core FitJob to read its Worker's cancellation token");
#endif
}

TEST_CASE("E05-T1 gates 4 6 a hidden fitted-input edit defeats stale publication") {
#if E05_T1_FIT_JOB
    for (bool equal_write : {false,true}) {
        auto live=e05_t1::small(); e04_t9::OwnerQueue queue; e05_t1::Trace trace;
        edi::work::Worker worker([&](auto d){queue.post(std::move(d));},{{},[&](const auto& e){trace.add(e);}});
        std::optional<edi::FitReport> final;
        edi::FitJob fit(live,worker,{{},{},{},[&](const auto& r){final=r;}});
        fit.start(); trace.finished();
        auto& parameter=live.experiment().linked_structure.scale;
        const double old=parameter.value; parameter.value=old*1.29;
        if(equal_write) parameter.value=old;
        const auto after_edit=edi::project_edi_files(live);
        while(!final) queue.one(); queue.drain();
        CHECK_MESSAGE((final->status==edi::FitStatus::SUPERSEDED), " gate 6 equal-value ABA writes and changed inputs supersede a completed queued fit");
        CHECK_MESSAGE((edi::project_edi_files(live)==after_edit), " gate 6 stale fit publishes no saved value error or snapshot over a hidden input edit");
    }
#else
    FAIL_CHECK(" gates 4 6 require atomic FitJob publication guarded against hidden input edits");
#endif
}

TEST_CASE("E05-T1 gate 5 scan calculation-only and invalid inputs are unchanged refusals") {
#if E05_T1_FIT_JOB
    for(const auto& reason : {"sequential","independent","calculation-only","invalid"}) {
        auto live=e05_t1::small();
        if(reason==std::string("calculation-only")) {
            live.experiment().data->write_column(&edi::PdDataBase::intensity_meas, {});
            live.experiment().data->write_column(&edi::PdDataBase::intensity_meas_su, {});
        } else if(reason==std::string("invalid")) live.experiment().data->write_column(&edi::PdDataBase::intensity_meas_su, std::vector<double>(24,0.0));
        else live.fitting_mode=reason;
        const auto before=edi::project_edi_files(live);
        e04_t9::OwnerQueue queue; edi::work::Worker worker([&](auto d){queue.post(std::move(d));});
        std::optional<edi::FitReport> final;
        edi::FitJob fit(live,worker,{{},{},{},[&](const auto& r){final=r;}});
        fit.start(); while(!final) queue.one(); queue.drain();
        CHECK_MESSAGE((!final->refusal.empty()), " gate 5 each refusal returns the core reason to the GUI");
        CHECK_MESSAGE((edi::project_edi_files(live)==before), " gate 5 refused jobs leave the complete saved project byte-identical");
    }
#else
    FAIL_CHECK(" gate 5 requires the core FitJob unchanged refusal path");
#endif
}

TEST_CASE("E05-T1 gate 6 data and Bragg hover contain all independently specified quantities") {
    edi::PatternSource source;
    source.x=std::make_shared<const std::vector<double>>(std::vector<double>{12.371});
    source.meas=std::make_shared<const std::vector<double>>(std::vector<double>{83.637});
    source.bkg=std::make_shared<const std::vector<double>>(std::vector<double>{7.251});
    source.calc=std::make_shared<const std::vector<double>>(std::vector<double>{78.121});
    source.resid=std::make_shared<const std::vector<double>>(std::vector<double>{5.516});
    edi::PatternSeries point; point.kind=edi::SeriesKind::Measured; point.id="meas";
    point.rows={0}; point.points={{12.371,83.637}};
    const auto text=e05_t1::readout(source,point);
    for (const auto& value : {"12.37","83.64","7.25","78.12","5.52"})
        CHECK_MESSAGE((text.find(value)!=std::string::npos), " gate 6 data hover reports x measured background calculated and signed residual at the same source index");
    edi::PatternSource::Phase phase; phase.structure_id="garnet"; phase.label="Garnet";
    phase.position=source.x; phase.hkl=std::make_shared<const std::vector<std::array<std::int32_t,3>>>(std::vector<std::array<std::int32_t,3>>{{2,-1,3}});
    source.phases.push_back(phase);
    point.kind=edi::SeriesKind::BraggTicks; point.id="bragg/garnet";
    const auto tick=e05_t1::readout(source,point);
    CHECK_MESSAGE(((tick.find("Garnet")!=std::string::npos || tick.find("garnet")!=std::string::npos)), " gate 6 Bragg hover names its independent structure");
    CHECK_MESSAGE((tick.find("12.37")!=std::string::npos && tick.find("Miller indices: (2 -1 3)")!=std::string::npos), " gate 6 Bragg hover includes x and the signed Miller tuple");
}

TEST_CASE("E05-T1 gate 8 fit-stream and GUI ADRs describe the shipped fitting contract") {
    const auto read_adr = [](const char* path) {
        std::ifstream file(path);
        return std::string((std::istreambuf_iterator<char>(file)), {});
    };
    const auto worker = read_adr("docs/dev/adrs/0020-calculation-worker-and-publication.md");
    const auto gui = read_adr("docs/dev/adrs/0017-app-gui-design.md");
    CHECK_MESSAGE((worker.find("FitJob")!=std::string::npos && worker.find("cancel")!=std::string::npos),
                  " gate 8 worker ADR names the fit-stream path and cancellation contract");
    CHECK_MESSAGE((gui.find("Undo and redo stay disabled.")==std::string::npos && gui.find("Miller indices")!=std::string::npos),
                  " gate 8 GUI ADR updates prior Undo behavior and specifies the full Bragg read-out");
}

#if E05_T1_FIT_JOB
namespace e05_t1 {
void publication_inputs(const std::string& mode, const std::string& terminal, const std::string& input) {
    INFO(mode); INFO(std::string(input)); INFO(terminal);
    auto live=small(mode);
    live.minimizer_max_iterations=terminal=="maxiter"?1:20;
    e04_t9::OwnerQueue queue; Trace trace; e04_t9::Barrier checkpoint;
    edi::work::Worker worker([&](auto d){queue.post(std::move(d));},
                             {{},[&](const auto& e){trace.add(e);}});
    std::optional<edi::FitReport> final;
    edi::FitJob fit(live,worker,{{},{},{},[&](const auto& r){final=r;}},
                     {[&](int poll){if(poll==1) checkpoint.block();}});
    REQUIRE_MESSAGE((fit.start()), " gate 6 boundary witness starts an actual fit job");
    checkpoint.entered();
    if(terminal=="cancelled") fit.cancel();
    checkpoint.release(); trace.finished();
    REQUIRE_MESSAGE((!final.has_value()), " gate 6 escaped write occurs after worker finish before queued final delivery");
    auto& parameter=live.experiment().linked_structure.scale;
    const std::string which=input;
    if(which=="mode") live.fitting_mode="independent";
    else if(which=="descent") live.descent="fast_descent";
    else if(which=="max-iterations") live.minimizer_max_iterations=37;
    else if(which=="chi-square-stop") live.minimizer_chi_square_tolerance=.012375;
    else if(which=="minimizer-type") live.minimizer_type="changed-after-fit";
    else if(which=="bank-weight") live.experiments[1]->dataset_weight=3.731;
    else if(which=="uncertainty" || which=="uncertainty-aba") {
        const auto old=parameter.uncertainty.get(); parameter.uncertainty=.731;
        if(which=="uncertainty-aba") parameter.uncertainty=old;
    } else if(which=="undo-value" || which=="undo-value-aba") {
        const auto old=parameter.start_value.get(); parameter.start_value=7.3125;
        if(which=="undo-value-aba") parameter.start_value=old;
    } else if(which=="undo-uncertainty" || which=="undo-uncertainty-aba") {
        const auto old=parameter.start_uncertainty.get(); parameter.start_uncertainty=.04375;
        if(which=="undo-uncertainty-aba") parameter.start_uncertainty=old;
    } else {
        const bool old=parameter.free; parameter.free=!old;
        if(which=="free-aba") parameter.free=old;
    }
    const auto edited=edi::project_edi_files(live);
    while(!final) queue.one(); queue.drain();
    REQUIRE_MESSAGE((final->result.has_value()), " gate 6 superseded boundary exercised a real terminal fit result");
    const auto expected=terminal=="cancelled"?edi::FitStatus::CANCELLED:
                        terminal=="maxiter"?edi::FitStatus::MAX_ITER:edi::FitStatus::DONE;
    CHECK_MESSAGE((final->result->status==expected), " gate 6 stale witness reaches its declared completed cancelled or early-stop boundary");
    CHECK_MESSAGE((final->status==edi::FitStatus::SUPERSEDED), " gate 6 every fitting-only or undo-input write supersedes a queued final result");
    CHECK_MESSAGE((edi::project_edi_files(live)==edited), " gate 6 obsolete adoption overwrites no live parameter uncertainty setting bank statistic or Undo capture");
}
}
#endif

//  generated publication-input cases (generate_publication_cases.py).

TEST_CASE("E05-T1 gates 4 6 completed single queued fit rejects mode") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("single", "completed", "mode");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 completed single queued fit rejects descent") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("single", "completed", "descent");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 completed single queued fit rejects max-iterations") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("single", "completed", "max-iterations");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 completed single queued fit rejects chi-square-stop") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("single", "completed", "chi-square-stop");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 completed single queued fit rejects minimizer-type") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("single", "completed", "minimizer-type");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 completed single queued fit rejects uncertainty") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("single", "completed", "uncertainty");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 completed single queued fit rejects uncertainty-aba") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("single", "completed", "uncertainty-aba");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 completed single queued fit rejects free") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("single", "completed", "free");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 completed single queued fit rejects free-aba") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("single", "completed", "free-aba");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 completed single queued fit rejects undo-value") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("single", "completed", "undo-value");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 completed single queued fit rejects undo-value-aba") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("single", "completed", "undo-value-aba");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 completed single queued fit rejects undo-uncertainty") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("single", "completed", "undo-uncertainty");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 completed single queued fit rejects undo-uncertainty-aba") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("single", "completed", "undo-uncertainty-aba");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 completed joint queued fit rejects mode") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("joint", "completed", "mode");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 completed joint queued fit rejects descent") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("joint", "completed", "descent");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 completed joint queued fit rejects max-iterations") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("joint", "completed", "max-iterations");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 completed joint queued fit rejects chi-square-stop") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("joint", "completed", "chi-square-stop");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 completed joint queued fit rejects minimizer-type") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("joint", "completed", "minimizer-type");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 completed joint queued fit rejects uncertainty") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("joint", "completed", "uncertainty");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 completed joint queued fit rejects uncertainty-aba") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("joint", "completed", "uncertainty-aba");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 completed joint queued fit rejects free") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("joint", "completed", "free");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 completed joint queued fit rejects free-aba") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("joint", "completed", "free-aba");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 completed joint queued fit rejects bank-weight") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("joint", "completed", "bank-weight");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 completed joint queued fit rejects undo-value") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("joint", "completed", "undo-value");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 completed joint queued fit rejects undo-value-aba") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("joint", "completed", "undo-value-aba");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 completed joint queued fit rejects undo-uncertainty") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("joint", "completed", "undo-uncertainty");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 completed joint queued fit rejects undo-uncertainty-aba") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("joint", "completed", "undo-uncertainty-aba");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 cancelled single queued fit rejects mode") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("single", "cancelled", "mode");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 cancelled single queued fit rejects descent") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("single", "cancelled", "descent");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 cancelled single queued fit rejects max-iterations") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("single", "cancelled", "max-iterations");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 cancelled single queued fit rejects chi-square-stop") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("single", "cancelled", "chi-square-stop");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 cancelled single queued fit rejects minimizer-type") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("single", "cancelled", "minimizer-type");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 cancelled single queued fit rejects uncertainty") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("single", "cancelled", "uncertainty");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 cancelled single queued fit rejects uncertainty-aba") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("single", "cancelled", "uncertainty-aba");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 cancelled single queued fit rejects free") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("single", "cancelled", "free");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 cancelled single queued fit rejects free-aba") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("single", "cancelled", "free-aba");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 cancelled single queued fit rejects undo-value") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("single", "cancelled", "undo-value");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 cancelled single queued fit rejects undo-value-aba") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("single", "cancelled", "undo-value-aba");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 cancelled single queued fit rejects undo-uncertainty") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("single", "cancelled", "undo-uncertainty");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 cancelled single queued fit rejects undo-uncertainty-aba") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("single", "cancelled", "undo-uncertainty-aba");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 cancelled joint queued fit rejects mode") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("joint", "cancelled", "mode");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 cancelled joint queued fit rejects descent") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("joint", "cancelled", "descent");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 cancelled joint queued fit rejects max-iterations") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("joint", "cancelled", "max-iterations");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 cancelled joint queued fit rejects chi-square-stop") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("joint", "cancelled", "chi-square-stop");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 cancelled joint queued fit rejects minimizer-type") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("joint", "cancelled", "minimizer-type");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 cancelled joint queued fit rejects uncertainty") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("joint", "cancelled", "uncertainty");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 cancelled joint queued fit rejects uncertainty-aba") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("joint", "cancelled", "uncertainty-aba");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 cancelled joint queued fit rejects free") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("joint", "cancelled", "free");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 cancelled joint queued fit rejects free-aba") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("joint", "cancelled", "free-aba");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 cancelled joint queued fit rejects bank-weight") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("joint", "cancelled", "bank-weight");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 cancelled joint queued fit rejects undo-value") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("joint", "cancelled", "undo-value");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 cancelled joint queued fit rejects undo-value-aba") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("joint", "cancelled", "undo-value-aba");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 cancelled joint queued fit rejects undo-uncertainty") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("joint", "cancelled", "undo-uncertainty");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 cancelled joint queued fit rejects undo-uncertainty-aba") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("joint", "cancelled", "undo-uncertainty-aba");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 maxiter single queued fit rejects mode") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("single", "maxiter", "mode");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 maxiter single queued fit rejects descent") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("single", "maxiter", "descent");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 maxiter single queued fit rejects max-iterations") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("single", "maxiter", "max-iterations");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 maxiter single queued fit rejects chi-square-stop") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("single", "maxiter", "chi-square-stop");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 maxiter single queued fit rejects minimizer-type") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("single", "maxiter", "minimizer-type");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 maxiter single queued fit rejects uncertainty") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("single", "maxiter", "uncertainty");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 maxiter single queued fit rejects uncertainty-aba") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("single", "maxiter", "uncertainty-aba");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 maxiter single queued fit rejects free") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("single", "maxiter", "free");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 maxiter single queued fit rejects free-aba") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("single", "maxiter", "free-aba");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 maxiter single queued fit rejects undo-value") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("single", "maxiter", "undo-value");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 maxiter single queued fit rejects undo-value-aba") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("single", "maxiter", "undo-value-aba");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 maxiter single queued fit rejects undo-uncertainty") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("single", "maxiter", "undo-uncertainty");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 maxiter single queued fit rejects undo-uncertainty-aba") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("single", "maxiter", "undo-uncertainty-aba");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 maxiter joint queued fit rejects mode") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("joint", "maxiter", "mode");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 maxiter joint queued fit rejects descent") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("joint", "maxiter", "descent");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 maxiter joint queued fit rejects max-iterations") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("joint", "maxiter", "max-iterations");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 maxiter joint queued fit rejects chi-square-stop") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("joint", "maxiter", "chi-square-stop");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 maxiter joint queued fit rejects minimizer-type") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("joint", "maxiter", "minimizer-type");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 maxiter joint queued fit rejects uncertainty") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("joint", "maxiter", "uncertainty");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 maxiter joint queued fit rejects uncertainty-aba") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("joint", "maxiter", "uncertainty-aba");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 maxiter joint queued fit rejects free") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("joint", "maxiter", "free");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 maxiter joint queued fit rejects free-aba") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("joint", "maxiter", "free-aba");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 maxiter joint queued fit rejects bank-weight") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("joint", "maxiter", "bank-weight");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 maxiter joint queued fit rejects undo-value") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("joint", "maxiter", "undo-value");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 maxiter joint queued fit rejects undo-value-aba") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("joint", "maxiter", "undo-value-aba");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 maxiter joint queued fit rejects undo-uncertainty") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("joint", "maxiter", "undo-uncertainty");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}

TEST_CASE("E05-T1 gates 4 6 maxiter joint queued fit rejects undo-uncertainty-aba") {
#if E05_T1_FIT_JOB
    e05_t1::publication_inputs("joint", "maxiter", "undo-uncertainty-aba");
#else
    FAIL_CHECK(" gate 6 requires guarded final FitJob publication for fitting-only inputs");
#endif
}
