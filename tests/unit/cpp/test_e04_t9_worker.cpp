#include <doctest/doctest.h>
#include <atomic>
#include <bit>
#include <optional>
#include <thread>
#include <type_traits>
#include <limits>

namespace c13_t12_fault {
extern thread_local long remaining;
extern thread_local unsigned calls;
extern thread_local unsigned faults;
}
#include "e04_t9_support.hpp"

#if __has_include("edi/worker.hpp") && __has_include("edi/live_preview.hpp")
#include "edi/worker.hpp"
#include "edi/live_preview.hpp"
#include "edi/calculation.hpp"
#include <crysta/tokens.hpp>

namespace e04_t9_boundary {
struct AssignmentProxy {
    double& live;
    AssignmentProxy& operator=(int) { live = -7; throw std::runtime_error("proxy escape"); }
};
struct ConvertingValue {
    int& calls;
    operator double() const { ++calls; throw std::runtime_error("conversion escape"); }
};
struct CopyingRow : edi::AtomSite {
    inline static int copies = 0;
    CopyingRow() = default;
    CopyingRow(const CopyingRow& other) : edi::AtomSite(other) {
        ++copies; throw std::runtime_error("row copy escape");
    }
};
template<class Field, class Value>
concept Assignable = requires(Field& field, Value value) { edi::Edit::assign(field, value); };
template<class Row>
concept Appendable = requires(edi::ItemVec<Row>& rows, Row row) { edi::Edit::append(rows, row); };
template<class Row>
concept Erasable = requires(edi::ItemVec<Row>& rows) { edi::Edit::erase(rows, 0); };
struct ForeignStructure : edi::Structure {};
struct ForeignExperiment : edi::ExperimentBase {};
struct ForeignAtom : edi::AtomSite {};
struct ForeignTexture : edi::PrefOrient {};
inline bool admission_armed = false;
inline int admissions = 0;
inline double* admission_write = nullptr;
inline std::string admission(const std::string& id) {
    if (admission_armed) { ++admissions; *admission_write = -7; throw std::runtime_error("foreign admission escape"); }
    return id;
}
}
namespace edi {
#define E04_T9_FOREIGN_KEY(Type, Member) \
template<> struct KeyTraits<e04_t9_boundary::Type> { \
    static ItemKey& key(e04_t9_boundary::Type& row) { return row.Member; } \
    static const ItemKey& key(const e04_t9_boundary::Type& row) { return row.Member; } \
    static std::string canonical(const std::string& id) { return e04_t9_boundary::admission(id); } \
    static const char* category() { return "foreign test row"; } \
};
E04_T9_FOREIGN_KEY(ForeignStructure, name)
E04_T9_FOREIGN_KEY(ForeignExperiment, name)
E04_T9_FOREIGN_KEY(ForeignAtom, id)
E04_T9_FOREIGN_KEY(ForeignTexture, structure_id)
#undef E04_T9_FOREIGN_KEY
}

TEST_CASE("E04-T9 C4 closed factories exclude assignment conversion and copy escapes") {
    using namespace e04_t9_boundary;
    auto live = edi::load_project(e04_t9_fixture::silicon);
    e04_t9::OwnerQueue queue;
    edi::work::Worker worker([&](auto d) { queue.post(std::move(d)); });
    int edits = 0, publications = 0;
    edi::LivePreview preview(live, worker, {[&] { ++edits; }, [&](const auto&) { ++publications; }});
    CHECK_MESSAGE(((!Assignable<AssignmentProxy, int>)),
        " C4 a caller assignment proxy cannot manufacture an Edit");
    CHECK_MESSAGE(((!Assignable<decltype(live.structure().cell.length_a.value), ConvertingValue>)),
        " C4 a generic written-parameter target cannot bypass the validated value operation");
    CHECK_MESSAGE(((!Appendable<CopyingRow> && !Erasable<CopyingRow>)),
        " C4 caller row types cannot manufacture append or erase operations");
    CHECK_MESSAGE(((!Appendable<edi::Structure> && !Appendable<edi::BraggPdExperiment>)),
        " C4 loaded blocks enter only through their declared loaded-block factories");
    const auto before = edi::project_edi_files(live);
    int conversions = 0;
    CHECK_THROWS_AS_MESSAGE(edi::Edit::value(live.structure().cell.length_a, ConvertingValue{conversions}),
        std::runtime_error, " C4 throwing conversion is completed at manufacturing before an Edit exists");
    CHECK_MESSAGE((conversions == 1 && preview.newest_request() == 0 && edits == 0 && publications == 0),
        " C4 a refused value conversion cannot enter apply or schedule a calculation");
    CHECK_MESSAGE((edi::project_edi_files(live) == before),
        " C4 conversion factory refusal leaves every live saved byte unchanged");
    CopyingRow source; source.id = "copy_control";
    CopyingRow::copies = 0;
    edi::ItemVec<edi::AtomSite> rows;
    using ModelRowFactory = edi::Edit (*)(edi::ItemVec<edi::AtomSite>&, edi::AtomSite);
    const ModelRowFactory factory = &edi::Edit::append;
    auto operation = factory(rows, source);
    CHECK_NOTHROW_MESSAGE(operation(),
        " C4 supported row factory slices to the model row before storing the operation");
    CHECK_MESSAGE((CopyingRow::copies == 0 && rows.size() == 1 && rows.front()->id == "copy_control"),
        " C4 executing a supported append never runs a caller-derived row copy");
}

TEST_CASE("E04-T9 C4 named id rename zero-axis and foreign-owner refusals preserve pending work") {
    using namespace e04_t9_boundary;
    auto live = edi::load_project(e04_t9_fixture::silicon);
    const auto structure = live.structures.front();
    const auto bank = live.experiments.front();
    const auto site = structure->atom_sites.front();
    auto second_structure = std::make_shared<edi::Structure>(*structure); second_structure->name = "structure";
    edi::ItemVec<edi::Structure> named_structures;
    auto named_structure = std::make_shared<edi::Structure>(*structure);
    named_structures.push_back(named_structure); named_structures.push_back(second_structure);
    auto second_bank = std::make_shared<edi::BraggPdExperiment>(*bank); second_bank->name = "experiment";
    live.experiments.push_back(second_bank);
    auto second_site = std::make_shared<edi::AtomSite>(*site); second_site->id = "other_atom";
    structure->atom_sites.push_back(second_site);
    auto texture = std::make_shared<edi::PrefOrient>(); texture->structure_id = structure->name.value();
    edi::ItemVec<edi::PrefOrient> named_textures; named_textures.push_back(texture);
    auto other_texture = std::make_shared<edi::PrefOrient>(); other_texture->structure_id = "structure";
    named_textures.push_back(other_texture);
    structure->scattering_lengths_fm.modify([](auto& lengths) {
        lengths["e04_first"] = 4.25;
        lengths["e04_second"] = 5.75;
    });
    edi::ItemVec<ForeignStructure> foreign_structures;
    edi::ItemVec<ForeignExperiment> foreign_banks;
    edi::ItemVec<ForeignAtom> foreign_sites;
    edi::ItemVec<ForeignTexture> foreign_textures;
    auto fs = std::make_shared<ForeignStructure>(); fs->name = "foreign_structure"; foreign_structures.push_back(fs);
    auto fe = std::make_shared<ForeignExperiment>(); fe->name = "foreign_bank"; foreign_banks.push_back(fe);
    auto fa = std::make_shared<ForeignAtom>(); fa->id = "foreign_atom"; foreign_sites.push_back(fa);
    auto ft = std::make_shared<ForeignTexture>(); ft->structure_id = "foreign_texture"; foreign_textures.push_back(ft);
    double foreign_write = 9.25;
    admission_write = &foreign_write; admissions = 0; admission_armed = true;
    // Always disarm on unwinding; no foreign collection outlives its armed rule.
    struct Disarm { ~Disarm() { admission_armed = false; admission_write = nullptr; } } disarm;
    e04_t9::OwnerQueue queue; e04_t9::Barrier first;
    edi::work::Worker worker([&](auto d) { queue.post(std::move(d)); });
    int calculations = 0, edits = 0, publications = 0;
    edi::LivePreview preview(live, worker, {[&] { ++edits; }, [&](const auto& result) {
        ++publications;
        CHECK_MESSAGE((result.generation == 1), " C4 pending admitted generation retains its final position after every refusal");
    }}, {[&](auto& snapshot, const auto& token) { ++calculations; first.block(); return edi::calculate(snapshot, token); }});
    preview.recalculate(); first.entered();
    const auto before = edi::snapshot_for_work(live).stamps;
    const auto bytes = edi::project_edi_files(live);
    const auto structure_generation = named_structures.generation();
    const auto texture_generation = named_textures.generation();
    const auto structure_id = named_structure->name.value();
    const auto texture_id = texture->structure_id.value();
    const std::vector<std::pair<const char*, std::function<edi::Edit()>>> refusals{
        {"structure duplicate id", [&] { return edi::Edit::structure_name(*named_structure, "structure"); }},
        {"structure empty canonical duplicate id", [&] { return edi::Edit::structure_name(*named_structure, ""); }},
        {"experiment duplicate rename", [&] { return edi::Edit::rename_experiment(live, *bank, "experiment"); }},
        {"experiment empty canonical duplicate rename", [&] { return edi::Edit::rename_experiment(live, *bank, ""); }},
        {"atom duplicate rename", [&] { return edi::Edit::rename_atom_site(*structure, *site, "other_atom"); }},
        {"texture duplicate id", [&] { return edi::Edit::texture_structure(*texture, "structure"); }},
        {"scattering duplicate rename", [&] { return edi::Edit::rename_scattering_length(*structure, "e04_first", "e04_second"); }},
        {"scattering empty rename", [&] { return edi::Edit::rename_scattering_length(*structure, "e04_first", ""); }},
        {"scattering absent source", [&] { return edi::Edit::rename_scattering_length(*structure, "absent", "new"); }},
        {"texture zero axis", [&] { return edi::Edit::texture_axis_component(*texture, &edi::PrefOrient::index_l, 0); }},
        {"texture axis bound", [&] { return edi::Edit::texture_axis_component(*texture, &edi::PrefOrient::index_h, edi::kPreferredOrientationAxisBound + 1); }},
        {"duplicate texture append", [&] { return edi::Edit::append(named_textures, *texture); }},
        {"foreign structure owner", [&] { return edi::Edit::structure_name(*fs, "new"); }},
        {"foreign experiment owner", [&] { return edi::Edit::rename_experiment(live, *fe, "new"); }},
        {"foreign atom owner", [&] { return edi::Edit::rename_atom_site(*structure, *fa, "new"); }},
        {"foreign texture owner", [&] { return edi::Edit::texture_structure(*ft, "new"); }}
    };
    for (const auto& [name, factory] : refusals) {
        INFO(name);
        CHECK_THROWS_AS_MESSAGE(preview.apply(factory()), std::exception,
            " C4 each named boundary refusal propagates before any live write");
        const auto after = edi::snapshot_for_work(live).stamps;
        CHECK_MESSAGE((before.experiment_inputs == after.experiment_inputs && before.structure_inputs == after.structure_inputs &&
            before.experiments == after.experiments && before.structures == after.structures &&
            before.experiments_generation == after.experiments_generation && before.structures_generation == after.structures_generation &&
            before.edits == after.edits && before.edits_at == after.edits_at),
            " C4 boundary refusal preserves all membership input and editor stamps");
        CHECK_MESSAGE((edi::project_edi_files(live) == bytes && live.structures.front() == structure &&
            live.experiments.front() == bank && structure->atom_sites.front() == site && named_textures.front() == texture && named_structures.front() == named_structure &&
            named_structures.generation() == structure_generation && named_textures.generation() == texture_generation &&
            named_structure->name == structure_id && texture->structure_id == texture_id),
            " C4 boundary refusal preserves saved bytes and every held model record");
        CHECK_MESSAGE((preview.newest_request() == 1 && edits == 0 && publications == 0),
            " C4 boundary refusal neither notifies an edit nor replaces pending work");
        CHECK_MESSAGE((admissions == 0 && foreign_write == 9.25 && fs->name == "foreign_structure" && fe->name == "foreign_bank" &&
            fa->id == "foreign_atom" && ft->structure_id == "foreign_texture"),
            " C4 foreign owner is refused before caller admission can write or throw");
        CHECK_MESSAGE((texture->index_h == 0 && texture->index_k == 0 && texture->index_l == 1),
            " C4 zero-axis and bound refusals restore the exact admitted direction");
    }
    first.release(); queue.one();
    CHECK_MESSAGE((calculations == 1 && publications == 1 && !preview.busy()),
        " C4 refused operations preserve the sole pending calculation and its final delivery");
    admission_armed = false;
    edi::Structure detached;
    CHECK_NOTHROW_MESSAGE(edi::Edit::structure_name(detached, "detached_control")(),
        " C4 detached model id has no foreign admission rule and remains supported");
    CHECK_MESSAGE(detached.name == "detached_control", " C4 detached model control actually performs the declared id write");
}

TEST_CASE("E04-T9 I2 I3 I4 I5 worker preserves every ordered delivery and cancellation") {
    e04_t9::OwnerQueue queue;
    e04_t9::Barrier first;
    const auto owner = std::this_thread::get_id();
    std::vector<int> deliveries;
    std::vector<edi::work::Event> events;
    std::mutex event_mutex;
    std::atomic<std::uint64_t> time{100};
    std::atomic<bool> cancelled{false};
    edi::work::Worker worker([&](auto d) { queue.post(std::move(d)); },
        {[&] { return time.fetch_add(1500000); }, [&](const auto& e) { std::lock_guard lock(event_mutex); events.push_back(e); }});
    auto delivery = [&](int n) { return [&, n] {
        CHECK_MESSAGE((std::this_thread::get_id() == owner), " I5 every delivery runs on its owner thread");
        deliveries.push_back(n);
    }; };
    const auto ticket = worker.submit("preview", [&](const auto& token, const auto& emit) {
        first.block();
        cancelled = token.cancelled();
        emit(delivery(1)); emit(delivery(2)); emit(delivery(3));
        return delivery(4);
    });
    first.entered();
    const auto next = worker.submit("fit", [&](const auto&, const auto& emit) {
        emit(delivery(5)); emit(delivery(6)); return delivery(7);
    });
    worker.cancel(ticket);
    CHECK_MESSAGE((deliveries.empty()), " I5 jobs never directly execute owner deliveries");
    first.release();
    for (int i = 0; i < 7; ++i) queue.one();
    CHECK_MESSAGE(((deliveries == std::vector<int>{1,2,3,4,5,6,7})),
                  " I3 cancellation does not drop final or emitted deliveries across channels");
    CHECK_MESSAGE((cancelled.load()), " I4 cancellation reaches the blocked running job token");
    CHECK_MESSAGE((ticket == 1 && next == 2), " P2 tickets advance in submission order");
    // A final fence means no worker trace can still be appending to the test log.
    worker.submit("fence", [&](const auto&, const auto&) { return delivery(8); }); queue.one();
    std::vector<std::uint64_t> starts;
    std::lock_guard event_lock(event_mutex);
    for (const auto& e : events) {
        if (e.kind == edi::work::EventKind::Started) {
            starts.push_back(e.id);
            CHECK_MESSAGE((e.thread != owner), " I2 every job executes on the worker thread");
        }
        CHECK_MESSAGE(((e.at_ns - 100) % 1500000 == 0),
                      " I6 every event reads the test's injected monotonic clock");
    }
    CHECK_MESSAGE(((starts == std::vector<std::uint64_t>{1,2,3})), " I2 one worker starts jobs serially in submission order");
}

TEST_CASE("E04-T9 worker destruction suppresses queued deliveries and cancels all tokens") {
    e04_t9::OwnerQueue queue;
    std::atomic<int> calls{0};
    std::atomic<bool> seen{false};
    std::atomic<bool> entered{false};
    auto worker = std::make_unique<edi::work::Worker>([&](auto d) { queue.post(std::move(d)); });
    worker->submit("fit", [&](const auto& token, const auto&) {
        entered = true;
        // A controlled cancellation checkpoint, no sleep. Destruction is the only releaser.
        const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(2);
        while (!token.cancelled() && std::chrono::steady_clock::now() < deadline) std::this_thread::yield();
        seen = token.cancelled();
        return [&] { ++calls; };
    });
    const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds(2);
    while (!entered.load() && std::chrono::steady_clock::now() < deadline) std::this_thread::yield();
    REQUIRE_MESSAGE(entered.load(), " I2 destructor control must reach an executing job");
    worker->submit("queued", [&](const auto&, const auto&) { return [&] { ++calls; }; });
    worker.reset(); queue.drain();
    CHECK_MESSAGE((seen.load()), " I3 destructor sets the running job's cancellation token before joining");
    CHECK_MESSAGE((calls.load() == 0), " I3 queued closures cannot act after worker destruction");
    CHECK_MESSAGE((!edi::work::Worker::any_alive()), " I1a the final worker destruction releases registration guard");
}

TEST_CASE("E04-T9 C1 C2 C3 C4 C7 C8 newest previews and independent ordered stream") {
    for (const int scenario : {1,2,3,4,7,8,9}) {
        INFO(scenario);
        auto project = edi::load_project(e04_t9_fixture::silicon);
        e04_t9::OwnerQueue queue;
        e04_t9::Barrier first;
        std::atomic<int> calculations{0};
        std::atomic<bool> cancellation_seen{false};
        std::vector<int> stream;
        std::vector<std::uint64_t> generations;
        std::vector<std::pair<double,double>> states;
        const auto owner = std::this_thread::get_id();
        edi::work::Worker worker([&](auto d) { queue.post(std::move(d)); });
        edi::LivePreview preview(project, worker,
            {[]{}, [&](const auto& result) {
                generations.push_back(result.generation);
                states.emplace_back(project.structure().cell.length_a.value,
                                    project.experiment().instrument.calib_d_to_tof_offset.value);
                CHECK_MESSAGE((project.experiment().computed_current()), " I9 published result has current computed categories");
                CHECK_MESSAGE((std::this_thread::get_id() == owner), " I5 hook executes in owner queue");
            }},
            {[&](auto& snapshot, const auto& token) {
                if (++calculations == 1) first.block();
                cancellation_seen = cancellation_seen.load() || token.cancelled();
                return edi::calculate(snapshot, token);
            }});
        const auto a = project.structure().cell.length_a.value;
        const auto b = project.experiment().instrument.calib_d_to_tof_offset.value;
        preview.apply(edi::Edit::value(project.structure().cell.length_a, a + .01));
        first.entered();
        if (scenario == 4) {
            // The committed option-B contract replaces arbitrary callbacks with declared edits.
            // Refusals preserve the held live records, stamps, newest request and pending v1.
            const auto prior_structure = project.structures.front();
            const auto prior_experiment = project.experiments.front();
            const auto* prior_data_identity = &*project.experiment().data;
            const auto prior_name = project.structure().name;
            const auto prior_free = project.structure().cell.length_a.free;
            const auto prior_description = project.metadata.description;
            const auto prior_measured = project.experiment().data->intensity_meas;
            const auto before = edi::snapshot_for_work(project).stamps;
            const auto callback = [&] { project.structure().cell.length_a.value = a + .03; };
            using Apply = decltype(static_cast<void (edi::LivePreview::*)(const edi::Edit&, bool*)>(&edi::LivePreview::apply));
            CHECK_MESSAGE((!std::is_invocable_v<Apply, edi::LivePreview&, decltype(callback)>),
                          " C4 the edit door cannot accept a raw state-writing lambda");
            CHECK_MESSAGE((!std::is_invocable_v<Apply, edi::LivePreview&, std::function<void()>>),
                          " C4 type erasure cannot carry arbitrary callbacks through the edit door");
            CHECK_MESSAGE((!std::is_constructible_v<edi::Edit, decltype(callback)> &&
                           !std::is_constructible_v<edi::Edit, std::function<void()>>),
                          " C4 callers cannot construct declared edits from arbitrary callbacks");
            const std::vector<std::function<edi::Edit()>> refused_edits{
                [&] { return edi::Edit::value(prior_structure->cell.length_a, -1.0); },
                [&] { return edi::Edit::project_name(project, "bad/name"); },
                [&] { return edi::Edit::fitting_mode(project, "not-a-mode"); },
                [&] { return edi::Edit::descent(project, "not-a-descent"); },
                [&] { return edi::Edit::max_iterations(project, 0); },
                [&] { return edi::Edit::chi_square_tolerance(project, -1.0); },
                [&] { return edi::Edit::peak_profile(*prior_experiment, "not-a-profile"); },
                [&] { return edi::Edit::absorption(*prior_experiment, "not-an-absorption"); },
                [&] { return edi::Edit::scattering_source(*prior_experiment,
                    edi::ScatteringSourceItem::NEUTRON_SCATTERING_LENGTH, "not-a-source"); },
                [&] { return edi::Edit::rename_scattering_length(*prior_structure, "not-declared", "Si"); },
                [&] { return edi::Edit::append(prior_structure->atom_sites, *prior_structure->atom_sites.front()); },
                [&] { return edi::Edit::add_experiments(project, {*prior_experiment}); },
                [&] { return edi::Edit::erase(project.structures, project.structures.size()); },
                [&] { return edi::Edit::erase(project.experiments, project.experiments.size()); },
                [&] { return edi::Edit::erase_excluded_region(*prior_experiment, prior_experiment->excluded_regions.size()); },
                [&] { return edi::Edit::excluded_region_bound(*prior_experiment,
                    prior_experiment->excluded_regions.size(), false, .25); },
                [&] { return edi::Edit::add_structure(project, *prior_structure); },
                [&] { auto unique = *prior_experiment; unique.name = "e04_t9_new_bank";
                    return edi::Edit::add_experiments(project, {unique, *prior_experiment}); }
            };
            for (std::size_t operation = 0; operation < refused_edits.size(); ++operation) {
                INFO("C4 declared operation ", operation);
                CHECK_THROWS_AS_MESSAGE(preview.apply(refused_edits[operation]()), std::exception,
                    " C4 each refusing declared operation propagates its refusal");
                const auto after = edi::snapshot_for_work(project).stamps;
                CHECK_MESSAGE((before.experiment_inputs == after.experiment_inputs &&
                               before.structure_inputs == after.structure_inputs &&
                               before.experiments == after.experiments && before.structures == after.structures &&
                               before.experiments_generation == after.experiments_generation &&
                               before.structures_generation == after.structures_generation &&
                               before.edits == after.edits && before.edits_at == after.edits_at),
                              " C4 refusal leaves calculation inputs membership identities and editor stamps unchanged");
                CHECK_MESSAGE(preview.newest_request() == 1,
                              " C4 a refused declared edit creates no new request");
                CHECK_MESSAGE((project.structure().cell.length_a.value == a + .01 &&
                               project.experiment().instrument.calib_d_to_tof_offset.value == b),
                              " I10 refusal leaves both pending parameter values unchanged");
                CHECK_MESSAGE((project.structures.front() == prior_structure &&
                               project.experiments.front() == prior_experiment &&
                               &*project.experiment().data == prior_data_identity),
                              " C4 refusal preserves held structure experiment and data identities");
                CHECK_MESSAGE((prior_structure->name == prior_name &&
                               prior_structure->cell.length_a.free == prior_free &&
                               project.metadata.description == prior_description &&
                               project.experiment().data->intensity_meas == prior_measured),
                              " I10 refusal leaves structure free state metadata and measured rows unchanged");
            }
        } else if (scenario == 7) {
            project.structure().cell.length_a.value = a + .05;
        } else {
            if (scenario == 8) worker.submit("fit", [&](const auto&, const auto& emit) {
                for (int n = 1; n <= 5; ++n) emit([&, n] { stream.push_back(n); });
                return [&] { stream.push_back(6); };
            });
            if (scenario != 1 && scenario != 9)
                preview.apply(edi::Edit::value(project.experiment().instrument.calib_d_to_tof_offset, b + .2));
            else preview.apply(edi::Edit::value(project.structure().cell.length_a, a + .02));
            preview.apply(edi::Edit::value(project.structure().cell.length_a, a + .05));
            if (scenario != 1 && scenario != 9)
                preview.apply(edi::Edit::value(project.experiment().instrument.calib_d_to_tof_offset, b + .4));
            else preview.apply(edi::Edit::value(project.structure().cell.length_a, a + .05));
            if (scenario == 3) preview.apply(edi::Edit::structure_name(project.structure(), "edited while blocked"));
            CHECK_MESSAGE((project.structure().cell.length_a.value == a + .05 && project.experiment().instrument.calib_d_to_tof_offset.value == b + ((scenario == 1 || scenario == 9) ? 0 : .4)),
                          " I10 edits apply immediately while a calculation is blocked");
            CHECK_MESSAGE((generations.empty()), " C9 no obsolete state publishes during continuous newer inputs");
        }
        const auto expected_generation = preview.newest_request();
        first.release();
        // One delivery for each preview and the six stream deliveries, all queued FIFO.
        queue.one();
        if (scenario == 8) for (int n = 0; n < 6; ++n) queue.one();
        if (scenario != 4) {
            CHECK_MESSAGE((generations.empty()), " I8 I11 stale or superseded first result cannot publish");
            queue.one();
        }
        CHECK_MESSAGE((generations == std::vector<std::uint64_t>{expected_generation}),
                      " I7 I9 exactly the final request publishes after inputs stop");
        CHECK_MESSAGE((calculations.load() == (scenario == 4 ? 1 : 2)),
                      " C1 burst coalesces to exactly one follow-up calculation");
        REQUIRE_MESSAGE(!states.empty(), " I9 final publication must exist before its state can be inspected");
        CHECK_MESSAGE((states.back().first == a + (scenario == 4 ? .01 : .05)),
                      " C2 newest publication holds the final first-key edit");
        CHECK_MESSAGE((states.back().second == b + ((scenario == 1 || scenario == 4 || scenario == 7 || scenario == 9) ? 0 : .4)),
                      " C2 newest publication holds all final second-key edits together");
        CHECK_MESSAGE((!preview.busy()), " C6 no calculation remains owed after final publication");
        if (scenario == 8) CHECK_MESSAGE(((stream == std::vector<int>{1,2,3,4,5,6})),
                                        " I3a rejected previews do not drop ordered stream deliveries");
        if (scenario != 4 && scenario != 7) CHECK_MESSAGE((cancellation_seen.load()),
            " I4 admitted requests cancel the calculation in flight");
    }
}

TEST_CASE("E04-T9 I12 I13 transaction stamps every bank structure membership and editor") {
    using Edit = std::function<void(edi::Project&)>;
    const std::vector<Edit> edits{
        [](auto& p) { p.experiments.back()->instrument.calib_d_to_tof_offset.value += .125; },
        [](auto& p) { p.structure().cell.length_a.value += .125; },
        [](auto& p) { auto e = p.experiments.back(); p.experiments.erase_at(p.experiments.size()-1); p.experiments.push_back(e); },
        [](auto& p) { auto s = p.structures.front(); p.structures.clear(); p.structures.push_back(s); },
        [](auto& p) { p.note_edit(); },
        [](auto& p) { auto& d = *p.experiment().data; std::vector<double> v = d.intensity_meas.get(); v[0] += .25; d.write_column(&edi::PdDataBase::intensity_meas, std::move(v)); }
    };
    std::size_t attack = 0;
    for (const auto& edit : edits) {
        INFO("I12 stamp attack index ", attack++);
        auto project = edi::load_project(e04_t9_fixture::wish);
        project.calculate();
        auto snapshot = edi::snapshot_for_work(project);
        CHECK_MESSAGE(snapshot.project.experiments.front().get() != project.experiments.front().get(),
                      " I1 snapshot experiments own separate mutable model records");
        CHECK_MESSAGE(snapshot.project.structures.front().get() != project.structures.front().get(),
                      " I1 snapshot structures own separate mutable model records");
        e04_t9::OwnerQueue queue;
        edi::work::Worker worker([&](auto d) { queue.post(std::move(d)); });
        std::optional<edi::CalculationResult> result;
        worker.submit("transaction", [&](const auto& token, const auto&) {
            result.emplace(edi::calculate(snapshot, token)); return []{};
        }); queue.one();
        edit(project);
        const auto before = edi::project_edi_files(project);
        REQUIRE_MESSAGE((result.has_value()), " I12 real snapshot calculation completed before currency attack");
        CHECK_MESSAGE((edi::publish(project, std::move(*result)) == edi::PublishOutcome::Superseded),
                      " I13 any bank structure membership or edit stamp change refuses publication");
        CHECK_MESSAGE((edi::project_edi_files(project) == before), " I13 superseded transaction writes no category or saved byte");
    }
}

TEST_CASE("E04-T9 I13a publication is byte-equivalent to the retained direct calculation") {
    for (const auto& path : e04_t9::projects()) {
        INFO(path);
        auto project = edi::load_project(path);
        auto direct = edi::load_project(path);
        // Missing fixture timestamps are generated at load and may straddle a second.
        // Establish identical input metadata; every output byte is still compared.
        direct.metadata.created = project.metadata.created;
        direct.metadata.last_modified = project.metadata.last_modified;
        direct.calculate();
        auto snapshot = edi::snapshot_for_work(project);
        e04_t9::OwnerQueue queue;
        edi::work::Worker worker([&](auto d) { queue.post(std::move(d)); });
        std::optional<edi::CalculationResult> result;
        worker.submit("transaction", [&](const auto& token, const auto&) {
            result.emplace(edi::calculate(snapshot, token)); return []{};
        }); queue.one();
        CHECK_MESSAGE((edi::publish(project, std::move(*result)) == edi::PublishOutcome::Published),
                      " seam 11 snapshot stamps come from live identities, not the copied records");
        for (std::size_t b = 0; b < project.experiments.size(); ++b)
            CHECK_MESSAGE((project.experiments[b]->computed_current() == direct.experiments[b]->computed_current()),
                          " I13a every published bank has direct-path currency");
        for (std::size_t s = 0; s < project.structures.size(); ++s)
            CHECK_MESSAGE((project.structures[s]->geometry_current() == direct.structures[s]->geometry_current()),
                          " I13a every published structure has direct-path geometry currency");
        for (std::size_t b=0;b<project.experiments.size();++b) {
            const auto& actual=project.experiments[b]->data->intensity_calc;
            const auto& expected=direct.experiments[b]->data->intensity_calc;
            REQUIRE_MESSAGE(actual.size()==expected.size(), " I13a published calculated columns retain all direct-path rows before any lazy save");
            for (std::size_t r=0;r<actual.size();++r)
                CHECK_MESSAGE(std::bit_cast<std::uint64_t>(actual[r])==std::bit_cast<std::uint64_t>(expected[r]),
                              " I13a published calculated values equal direct-path bits before any lazy read");
        }
        CHECK_MESSAGE((edi::project_edi_files(project) == edi::project_edi_files(direct)),
                      " I13a published computed categories and geometry save exactly like direct calculation");
    }
}

TEST_CASE("E04-T9 I1a registration refuses while any worker exists") {
    bool refused = false;
    {
        e04_t9::OwnerQueue queue;
        edi::work::Worker worker([&](auto d) { queue.post(std::move(d)); });
        try { edi::register_peak_type("e04_t9_guard", edi::BeamModeEnum::TIME_OF_FLIGHT); }
        catch (const std::logic_error&) { refused = true; }
        CHECK_MESSAGE((refused), " I1a registration throws logic_error before either registry can be mutated");
    }
    CHECK_MESSAGE((!edi::work::Worker::any_alive()), " I1a guard counts worker lifetime, not job activity");
    CHECK_NOTHROW_MESSAGE(edi::register_peak_type("e04_t9_guard", edi::BeamModeEnum::TIME_OF_FLIGHT),
                          " I1a registration resumes after the last worker is destroyed");
}
TEST_CASE("E04-T9 C5 newest refusal clears all computed categories without dropping final position") {
    for (bool supersedes : {false,true}) {
        auto live = edi::load_project(e04_t9_fixture::silicon); live.calculate();
        const std::string invalid_group = "e04_t9_not_a_space_group";
        // Independent engine resolver: the admitted text must refuse in crysta itself.
        CHECK_THROWS_AS_MESSAGE(crysta::space_group_from_file(invalid_group, std::nullopt), std::exception,
            " C5 the independent crysta resolver refuses the invalid group fixture");
        const auto measured = live.experiment().data->intensity_meas;
        e04_t9::OwnerQueue queue; e04_t9::Barrier first;
        edi::work::Worker worker([&](auto d){queue.post(std::move(d));});
        int calls = 0, publications = 0;
        edi::LivePreview preview(live,worker,{[]{},[&](const auto& result){
            ++publications;
            CHECK_MESSAGE(!result.refusal.empty(), " C5 newest real engine refusal is published with its reason");
            for (const auto& bank : live.experiments) CHECK_MESSAGE((!bank->data || bank->data->intensity_calc.empty()),
                " I13 a refused calculation clears every experiment's computed category");
        }},{[&](auto& snapshot,const auto& token){
            if (supersedes && ++calls == 1) first.block();
            return edi::calculate(snapshot,token);
        }});
        if (supersedes) { preview.recalculate(); first.entered(); }
        preview.apply(edi::Edit::assign(live.structure().space_group.name_h_m, invalid_group));
        if (supersedes) { first.release(); queue.one(); CHECK_MESSAGE(publications==0,
            " C5 obsolete successful calculation cannot publish before newest refusal"); }
        queue.one();
        CHECK_MESSAGE(publications==1, " C5 final refused request is published exactly once");
        CHECK_MESSAGE((live.experiment().data.has_value() && live.experiment().data->intensity_meas == measured),
            " C5 admitted invalid group retains the measured data while the real engine refuses");
        CHECK_MESSAGE(!preview.busy(), " C5 refusal ends the latest request without an infinite retry");
    }
}
// E11-T5 R1: existing trace instrumentation can fail at this genuine
// post-edit/post-snapshot, pre-submit boundary. It is not an allocation hook.
TEST_CASE("E11-T5 R1 pre-submit preparation failure preserves edit and permits real recovery") {
    auto live = edi::load_project(e04_t9_fixture::silicon);
    e04_t9::OwnerQueue queue;
    bool fail_once = true;
    int fired = 0, submissions = 0, edits = 0, publications = 0;
    edi::work::Worker worker([&](auto delivery) { queue.post(std::move(delivery)); },
        {{}, [&](const edi::work::Event& event) {
            if (event.channel != "preview") return;
            if (event.kind == edi::work::EventKind::Submitted) ++submissions;
            if (event.kind == edi::work::EventKind::Snapshot && fail_once) {
                fail_once = false; ++fired;
                throw std::runtime_error("original one-shot preparation observer refusal");
            }
        }});
    edi::LivePreview preview(live, worker,
        {[&] { ++edits; }, [&](const edi::PreviewResult&) { ++publications; }});
    const double original = live.structure().cell.length_a.value.get();
    CHECK_THROWS_AS(preview.apply(edi::Edit::value(live.structure().cell.length_a,
                                                original + 0.01)), std::runtime_error);
    REQUIRE(fired == 1);
    CHECK(live.structure().cell.length_a.value.get() == original + 0.01);
    CHECK(edits == 1);
    CHECK(publications == 0);
    CHECK(submissions == 0);
    // Busy may truthfully include owed work. The required property is that an
    // explicit normal retry can actually submit, not cancel a phantom ticket.
    preview.recalculate();
    REQUIRE(submissions == 1);
    queue.one();
    CHECK(publications == 1);
    CHECK_FALSE(preview.busy());
    CHECK(live.structure().cell.length_a.value.get() == original + 0.01);
    CHECK(fired == 1);
}


TEST_CASE("E11-T5 closed edits pin actual member before fallible preview observers") {
    using Result = edi::Edit::AppliedResult;
    static_assert(std::is_trivially_copyable_v<Result>);
    static_assert(std::is_same_v<decltype(Result{}.structure), const edi::Structure*>);
    static_assert(std::is_same_v<decltype(Result{}.experiment), const edi::ExperimentBase*>);
    // All FOUR original closed factories; direct success is independent of the fallible observers.
    for (int factory = 0; factory != 4; ++factory) {
        for (int entrance = 0; entrance != 3; ++entrance) {
            CAPTURE(factory);
            CAPTURE(entrance);
            auto live = edi::load_project(e04_t9_fixture::silicon);
            const auto original_structure = live.structures.front();
            const auto measured_source = live.experiments.front();
            REQUIRE_MESSAGE(measured_source->data.has_value(), "RECEIPT491 SETUP original reader fixture has actual measured data");
            const auto original_structure_count = live.structures.size();
            auto initial = edi::simulation_experiment("receipt491_target", {}, std::vector<std::string>{original_structure->name.value()});
            edi::Edit::create_experiment(live, std::move(initial))(); // Original ordinary setup; not the operation under test.
            const auto target = live.experiments.back();
            REQUIRE_MESSAGE(target->calculation_only, "RECEIPT491 SETUP original simulation target is genuinely eligible for replacement");
            const auto target_index = live.experiments.size() - 1;
            edi::Edit::create_experiment(live, edi::simulation_experiment(
                "receipt491_unrelated_tail", {}, std::vector<std::string>{original_structure->name.value()}))();
            const auto unrelated_tail = live.experiments.back();
            const auto count = live.experiments.size();
            const auto original_structure_text = edi::project_edi_files(live);
            auto make_operation = [&]() -> edi::Edit {
                if (factory == 0) {
                    auto structure = *original_structure;
                    structure.name = "receipt491_appended_structure";
                    return edi::Edit::add_structure(live, std::move(structure));
                }
                if (factory == 1)
                    return edi::Edit::create_experiment(live, edi::simulation_experiment(
                        "receipt491_appended_experiment", {}, std::vector<std::string>{original_structure->name.value()}));
                if (factory == 2) {
                    edi::ExperimentTypeTokens type;
                    type.radiation_probe = "xray";
                    return edi::Edit::replace_experiment(live, *target, edi::simulation_experiment(
                        "receipt491_target", type, std::vector<std::string>{original_structure->name.value()}));
                }
                auto loaded = *measured_source;
                loaded.name = "receipt491_loaded_experiment";
                return edi::Edit::load_data(live, *target, std::move(loaded));
            };
            const auto operation = make_operation();
            bool applied = true; // Each actual Input entrance must clear BOTH supplied destinations.
            Result result{original_structure.get(), target.get(), original_structure->atom_sites.front().get()};
            int inputs = 0, applied_events = 0, edited = 0;
            auto require_identity = [&] {
                if (entrance != 0) CHECK_MESSAGE(applied, "RECEIPT491 actual applied flag exists before every fallible observer");
                CHECK_MESSAGE(live.structures.front() == original_structure,
                              "RECEIPT491 original unrelated structure retains its actual identity");
                if (factory == 0) {
                    REQUIRE_MESSAGE(live.structures.size() == original_structure_count + 1,
                                    "RECEIPT491 structure factory executes exactly once");
                    CHECK_MESSAGE((result.structure == live.structures.back().get() && result.experiment == nullptr && result.atom == nullptr && result.exclusion == nullptr),
                                  "RECEIPT491 structure pin is the actual appended member before publication");
                    CHECK_MESSAGE(live.structures.back()->name == "receipt491_appended_structure",
                                  "RECEIPT491 actual appended identity belongs to the independent literal operation");
                } else {
                    REQUIRE_MESSAGE(live.experiments.size() == count + (factory == 1 ? 1 : 0),
                                    "RECEIPT491 experiment factory executes exactly once without duplicate members");
                    const auto actual_member = factory == 1 ? live.experiments.back() : live.experiments[target_index];
                    CHECK_MESSAGE(live.experiments[count - 1] == unrelated_tail,
                                  "RECEIPT491 replacement cannot select the unrelated later member by row position");
                    CHECK_MESSAGE((result.structure == nullptr && result.experiment == actual_member.get() && result.atom == nullptr && result.exclusion == nullptr),
                                  "RECEIPT491 experiment pin is the actual current appended/replacement member");
                    CHECK_MESSAGE(actual_member->name == (factory == 1 ? "receipt491_appended_experiment" :
                                  factory == 2 ? "receipt491_target" : "receipt491_loaded_experiment"),
                                  "RECEIPT491 receipt belongs to the independent literal closed operation");
                    if (factory >= 2)
                        CHECK_MESSAGE(result.experiment != target.get(),
                                      "RECEIPT491 replacement receipt never keeps the old still-live member pointer");
                    if (factory == 3) {
                        REQUIRE_MESSAGE(actual_member->data.has_value(),
                                        "RECEIPT491 real measurement replacement actually holds original data");
                        CHECK_MESSAGE(actual_member->data->intensity_meas.get() == measured_source->data->intensity_meas.get(),
                                      "RECEIPT491 measurement replacement preserves independent original reader observations");
                    }
                }
            };
            if (entrance == 0) {
                result = operation.apply_result(); // Executes ONCE, never a getter after a separate operator().
                require_identity();
            } else {
                e04_t9::OwnerQueue queue;
                edi::work::Worker worker([&](auto delivery) { queue.post(std::move(delivery)); },
                    {{}, [&](const edi::work::Event& event) {
                        if (event.kind == edi::work::EventKind::Input) {
                            ++inputs;
                            CHECK_MESSAGE((!applied && result.structure == nullptr && result.experiment == nullptr && result.atom == nullptr && result.exclusion == nullptr),
                                          "RECEIPT491 both caller destinations clear before the original Input trace");
                            CHECK_MESSAGE(edi::project_edi_files(live) == original_structure_text,
                                          "RECEIPT491 Input trace precedes the actual closed operation");
                        }
                        if (event.kind == edi::work::EventKind::Applied) {
                            ++applied_events;
                            require_identity();
                            if (entrance == 1) throw std::runtime_error("receipt491 Applied trace failure");
                        }
                    }});
                edi::LivePreview preview(live, worker, {[&] {
                    ++edited;
                    require_identity();
                    throw std::runtime_error("receipt491 edited publication failure");
                }, {}});
                const std::string expected = entrance == 1 ? "receipt491 Applied trace failure" : "receipt491 edited publication failure";
                bool exact_failure = false;
                try { preview.apply(operation, &applied, &result); }
                catch (const std::runtime_error& failure) { exact_failure = failure.what() == expected; }
                CHECK_MESSAGE(exact_failure, "RECEIPT491 reached real original fallible observer, never an earlier setup refusal");
                CHECK_MESSAGE((inputs == 1 && applied_events == 1 && edited == (entrance == 2 ? 1 : 0)),
                              "RECEIPT491 one actual Input/Applied boundary and expected original hook are reached");
                require_identity(); // Throw cannot erase factual applied state or its ORIGINAL identity.
            }
        }
    }
}

TEST_CASE("E11-T5 Input refusal clears applied identity before any closed edit") {
    auto live = edi::load_project(e04_t9_fixture::silicon);
    const auto before = edi::project_edi_files(live);
    bool applied = true;
    edi::Edit::AppliedResult result{live.structures.front().get(), live.experiments.front().get(), live.structures.front()->atom_sites.front().get()};
    int inputs = 0;
    e04_t9::OwnerQueue queue;
    edi::work::Worker worker([&](auto delivery) { queue.post(std::move(delivery)); },
        {{}, [&](const edi::work::Event& event) {
            if (event.kind != edi::work::EventKind::Input) return;
            ++inputs;
            CHECK_MESSAGE((!applied && result.structure == nullptr && result.experiment == nullptr && result.atom == nullptr && result.exclusion == nullptr),
                          "RECEIPT491 original Input observes cleared caller-owned storage");
            throw std::runtime_error("receipt491 refused at Input");
        }});
    edi::LivePreview preview(live, worker, {});
    auto structure = live.structure(); structure.name = "receipt491_must_not_append";
    const auto operation = edi::Edit::add_structure(live, std::move(structure));
    bool refused = false;
    try { preview.apply(operation, &applied, &result); }
    catch (const std::runtime_error& failure) { refused = std::string(failure.what()) == "receipt491 refused at Input"; }
    CHECK_MESSAGE((refused && inputs == 1 && !applied && result.structure == nullptr && result.experiment == nullptr && result.atom == nullptr && result.exclusion == nullptr),
                  "RECEIPT491 actual pre-write Input refusal has no false or inherited applied identity");
    CHECK_MESSAGE(edi::project_edi_files(live) == before, "RECEIPT491 Input refusal preserves every original scientific saved byte");
}

TEST_CASE("E11-T5 actual appended atom identity precedes fallible preview observers") {
    using Result=edi::Edit::AppliedResult;
    static_assert(std::is_same_v<decltype(Result{}.atom),const edi::AtomSite*>);
    for(int entrance=0;entrance!=3;++entrance) {
        CAPTURE(entrance);
        auto live=edi::load_project(e04_t9_fixture::silicon);
        const auto structure=live.structures.front();
        REQUIRE_MESSAGE(!structure->atom_sites.empty(),"ATOM634 SETUP original independent structure has an actual initial site");
        const auto first=structure->atom_sites.front();const auto count=structure->atom_sites.size();
        auto atom=*first;atom.id="Independent634_added";
        const auto operation=edi::Edit::append(structure->atom_sites,std::move(atom));
        const auto before=edi::project_edi_files(live);
        bool applied=true;Result result{structure.get(),live.experiments.front().get(),first.get()};
        int inputs=0,applied_events=0,edited=0;
        auto pin=[&]{
            REQUIRE_MESSAGE(structure->atom_sites.size()==count+1,"ATOM634 append executes exactly once");
            CHECK_MESSAGE(structure->atom_sites.front()==first,"ATOM634 original initial atom is preserved by append");
            CHECK_MESSAGE((result.atom==structure->atom_sites.back().get()&&result.atom!=first.get()&&result.structure==nullptr&&result.experiment==nullptr&&result.exclusion==nullptr),
                          "ATOM634 result pins EXACT inserted atom before every fallible observer, never the retained initial row");
            CHECK_MESSAGE(structure->atom_sites.back()->id=="Independent634_added","ATOM634 inserted pin owns the independently requested identity");
        };
        if(entrance==0){result=operation.apply_result();pin();continue;}
        e04_t9::OwnerQueue queue;
        edi::work::Worker worker([&](auto delivery){queue.post(std::move(delivery));},{{},[&](const edi::work::Event& event){
            if(event.kind==edi::work::EventKind::Input){++inputs;CHECK_MESSAGE((!applied&&result.structure==nullptr&&result.experiment==nullptr&&result.atom==nullptr&&result.exclusion==nullptr),
                "ATOM634 all FOUR stale caller pins clear before real Input");CHECK_MESSAGE(edi::project_edi_files(live)==before,"ATOM634 Input is genuinely before append");}
            if(event.kind==edi::work::EventKind::Applied){++applied_events;CHECK_MESSAGE(applied,"ATOM634 factual applied flag precedes trace");pin();
                if(entrance==1)throw std::runtime_error("atom634 Applied observer");}
        }});
        edi::LivePreview preview(live,worker,{[&]{++edited;CHECK_MESSAGE(applied,"ATOM634 factual applied flag precedes edited hook");pin();
            throw std::runtime_error("atom634 edited observer");},{}});
        bool exact=false;
        try{preview.apply(operation,&applied,&result);}catch(const std::runtime_error& error){exact=std::string(error.what())==(entrance==1?"atom634 Applied observer":"atom634 edited observer");}
        CHECK_MESSAGE(exact,"ATOM634 reached the original intended post-apply observer, not an earlier failure");
        CHECK_MESSAGE((inputs==1&&applied_events==1&&edited==(entrance==2?1:0)),"ATOM634 each original boundary occurs exactly once");
        pin(); // Later throw does not erase factual atom identity or apply again.
    }
}

TEST_CASE("E11-T5 actual exclusion pin precedes fallible preview observers") {
    using Result=edi::Edit::AppliedResult;
    static_assert(std::is_same_v<decltype(Result{}.exclusion),const edi::ExcludedRegion*>);
    for(int entrance=0;entrance!=3;++entrance) {
        CAPTURE(entrance);
        auto live=edi::load_project(e04_t9_fixture::silicon);
        const auto experiment=live.experiments.front();
        edi::Edit::append_excluded_region(*experiment,1.25,2.5)();
        const auto first=experiment->excluded_regions.back();const auto count=experiment->excluded_regions.size();
        const auto operation=edi::Edit::append_excluded_region(*experiment,3.75,9.125);
        const auto before=edi::project_edi_files(live);
        bool applied=true;Result result{live.structures.front().get(),experiment.get(),live.structures.front()->atom_sites.front().get(),first.get()};
        int inputs=0,applied_events=0,edited=0;
        auto pin=[&]{
            REQUIRE_MESSAGE(experiment->excluded_regions.size()==count+1,"EXPERIMENT643 append executes exactly once");
            CHECK_MESSAGE(experiment->excluded_regions[count-1]==first,"EXPERIMENT643 retained previous row is not mistaken for inserted member");
            CHECK_MESSAGE((result.structure==nullptr&&result.experiment==nullptr&&result.atom==nullptr&&result.exclusion==experiment->excluded_regions.back().get()&&result.exclusion!=first.get()),
                "EXPERIMENT643 actual inserted exclusion is pinned BEFORE every fallible observer");
            CHECK_MESSAGE((experiment->excluded_regions.back()->first==3.75&&experiment->excluded_regions.back()->second==9.125),
                "EXPERIMENT643 early actual member retains independently requested literal endpoints");
        };
        if(entrance==0){result=operation.apply_result();pin();continue;}
        e04_t9::OwnerQueue queue;
        edi::work::Worker worker([&](auto delivery){queue.post(std::move(delivery));},{{},[&](const edi::work::Event& event){
            if(event.kind==edi::work::EventKind::Input){++inputs;CHECK_MESSAGE((!applied&&result.structure==nullptr&&result.experiment==nullptr&&result.atom==nullptr&&result.exclusion==nullptr),
                "EXPERIMENT643 all FOUR stale caller pins clear BEFORE genuine Input");CHECK_MESSAGE(edi::project_edi_files(live)==before,"EXPERIMENT643 actual Input is before the write");}
            if(event.kind==edi::work::EventKind::Applied){++applied_events;CHECK_MESSAGE(applied,"EXPERIMENT643 actual applied flag precedes trace");pin();
                if(entrance==1)throw std::runtime_error("exclusion643 Applied failure");}
        }});
        edi::LivePreview preview(live,worker,{[&]{++edited;pin();throw std::runtime_error("exclusion643 edited failure");},{}});
        const std::string expected=entrance==1?"exclusion643 Applied failure":"exclusion643 edited failure";
        bool exact=false;try{preview.apply(operation,&applied,&result);}catch(const std::runtime_error& error){exact=std::string(error.what())==expected;}
        CHECK_MESSAGE((exact&&inputs==1&&applied_events==1&&edited==(entrance==2?1:0)),"EXPERIMENT643 exact real postwrite observer failure reached once");
        pin();CHECK_MESSAGE(applied,"EXPERIMENT643 later failure cannot erase factual original insertion");
    }
}

TEST_CASE("E11-T5 ordinary profile and exclusion restore preserve original scientific owners") {
    auto live=edi::load_project(e04_t9_fixture::echidna);
    const auto experiment=live.experiments.front();const auto structure=live.structures.front();
    REQUIRE_MESSAGE(experiment->data.has_value(),"EXPERIMENT643 independent committed Echidna input is genuinely measured");
    REQUIRE_MESSAGE(experiment->peak.broad_gauss_u.has_value(),"EXPERIMENT643 independent FCJ fixture has an engaged shared U cell");
    REQUIRE_MESSAGE(experiment->peak.asym_fcj_1.has_value(),"EXPERIMENT643 independent FCJ fixture has an optional field dropped by Gaussian");
    CHECK_MESSAGE(edi::effective_peak_type(*experiment)=="cwl-tch-pseudo-voigt-fcj","EXPERIMENT643 profile baseline comes from the committed fixture tag");
    auto* shared=&*experiment->peak.broad_gauss_u;const auto original_data=&*experiment->data;
    edi::Edit::value(*shared,.234567)();shared->free=true;shared->uncertainty=.012345;
    const auto before=edi::project_edi_files(live);
    auto undo=edi::capture_experiment_controls(live,*experiment,true);
    edi::Edit::peak_profile(*experiment,"cwl-gaussian")();
    CHECK_MESSAGE(edi::effective_peak_type(*experiment)=="cwl-gaussian","EXPERIMENT643 actual requested profile applied on measured target");
    CHECK_MESSAGE((experiment->peak.broad_gauss_u.has_value()&&&*experiment->peak.broad_gauss_u==shared),"EXPERIMENT643 shared engaged original parameter handle survives changed profile");
    CHECK_MESSAGE((shared->value.get()==.234567&&shared->free.get()&&shared->uncertainty.get()==std::optional<double>{.012345}),"EXPERIMENT643 shared scalar/free/SU remain exact nontrivial operands");
    CHECK_MESSAGE(!experiment->peak.asym_fcj_1.has_value(),"EXPERIMENT643 original selector actually drops FCJ-only field, never fakes preserved shape");
    edi::Edit::restore_experiment_controls(live,std::move(undo))();
    CHECK_MESSAGE(edi::project_edi_files(live)==before,"EXPERIMENT643 narrow profile restore returns every saved scientific field/SU/free/optional/relationship fact");
    CHECK_MESSAGE((live.experiments.front()==experiment&&live.structures.front()==structure&&&*experiment->data==original_data&&&*experiment->peak.broad_gauss_u==shared),
        "EXPERIMENT643 restore retains original experiment/structure/measured data/shared parameter owners");
    auto regions=edi::capture_experiment_controls(live,*experiment,false);
    edi::Edit::append_excluded_region(*experiment,0,0)();
    const auto index=experiment->excluded_regions.size()-1;
    edi::Edit::excluded_region_bound(*experiment,index,false,7.25)();
    edi::Edit::excluded_region_bound(*experiment,index,true,2.125)();
    CHECK_MESSAGE((experiment->excluded_regions[index]->first==7.25&&experiment->excluded_regions[index]->second==2.125),
        "EXPERIMENT643 ordinary finite reversed endpoints stay literal without sort/clamp");
    edi::Edit::restore_experiment_controls(live,std::move(regions))();
    CHECK_MESSAGE(edi::project_edi_files(live)==before,"EXPERIMENT643 exact narrow exclusion restore preserves all unrelated scientific saved bytes");
    const auto refused_before=edi::project_edi_files(live);
    bool wrong_mode=false;try{edi::Edit::peak_profile(*experiment,"tof-jorgensen")();}catch(const std::invalid_argument&){wrong_mode=true;}
    CHECK_MESSAGE((wrong_mode&&edi::project_edi_files(live)==refused_before),"EXPERIMENT643 actual wrong-beam profile refuses before scientific write");
}

TEST_CASE("E11-T5 original profile preparation refuses each reached allocation before live writes") {
    for(bool restore : {false,true}) {
        CAPTURE(restore);
        // Existing C13-T12 allocator: count the successful original operation,
        // then fail each actually reached allocation. No guessed sweep length.
        auto make=[&] {
            auto live=edi::load_project(e04_t9_fixture::echidna);
            return live;
        };
        auto warm=make();auto warm_undo=edi::capture_experiment_controls(warm,warm.experiment(),true);
        edi::Edit::peak_profile(warm.experiment(),"cwl-gaussian")();
        edi::Edit::restore_experiment_controls(warm,std::move(warm_undo))();
        auto measured=make();auto undo=edi::capture_experiment_controls(measured,measured.experiment(),true);
        if(restore)edi::Edit::peak_profile(measured.experiment(),"cwl-gaussian")();
        c13_t12_fault::calls=0;c13_t12_fault::faults=0;c13_t12_fault::remaining=std::numeric_limits<long>::max();
        try {
            if(restore)edi::Edit::restore_experiment_controls(measured,std::move(undo))();
            else edi::Edit::peak_profile(measured.experiment(),"cwl-gaussian")();
        } catch(...) {c13_t12_fault::remaining=-1;throw;}
        c13_t12_fault::remaining=-1;
        const auto allocations=c13_t12_fault::calls;
        CHECK_MESSAGE(c13_t12_fault::faults==0,"EXPERIMENT648 successful allocation-counting control genuinely commits");
        CHECK_MESSAGE(edi::effective_peak_type(measured.experiment())==(restore?"cwl-tch-pseudo-voigt-fcj":"cwl-gaussian"),
            "EXPERIMENT648 measured original factory/operation reaches literal requested control");
        for(unsigned allocation=0;allocation<allocations;++allocation) {
            CAPTURE(allocation);
            auto live=make();auto retained=edi::capture_experiment_controls(live,live.experiment(),true);
            if(restore)edi::Edit::peak_profile(live.experiment(),"cwl-gaussian")();
            const auto before=edi::project_edi_files(live);auto* shared=&*live.experiment().peak.broad_gauss_u;
            bool refused=false;c13_t12_fault::calls=0;c13_t12_fault::faults=0;c13_t12_fault::remaining=allocation;
            try {
                if(restore)edi::Edit::restore_experiment_controls(live,std::move(retained))();
                else edi::Edit::peak_profile(live.experiment(),"cwl-gaussian")();
            }catch(const std::bad_alloc&){refused=true;}catch(...){c13_t12_fault::remaining=-1;throw;}
            c13_t12_fault::remaining=-1;
            CHECK_MESSAGE((refused&&c13_t12_fault::faults==1),"EXPERIMENT648 each measured allocation escape actually reaches first owning failure seam");
            CHECK_MESSAGE(edi::project_edi_files(live)==before,"EXPERIMENT648 preparation failure leaves every original scientific saved byte unchanged");
            CHECK_MESSAGE(&*live.experiment().peak.broad_gauss_u==shared,"EXPERIMENT648 original shared parameter remains the same retained owner after refusal");
        }
    }
}

TEST_CASE("E11-T5 original supported profile domain preserves long escaped registered tokens") {
    REQUIRE_MESSAGE(!edi::work::Worker::any_alive(),"EXPERIMENT648 registration uses original pre-Worker public boundary");
    const std::vector<std::string> tokens={std::string(257,'p'),std::string(260,'q')+"\\\"\t",std::string("registered648_")+std::string(130,'x')+"\xce\xbb\xf0\x9f\x99\x82"};
    for(const auto& token:tokens)edi::register_peak_type(token,edi::BeamModeEnum::TIME_OF_FLIGHT);
    const auto offered=edi::supported_peak_profiles(edi::BeamModeEnum::TIME_OF_FLIGHT);
    for(const auto& token:tokens) {
        CHECK_MESSAGE(std::find(offered.begin(),offered.end(),token)!=offered.end(),"EXPERIMENT648 original registry offers exact extension token without member-ID restriction");
        auto live=edi::load_project(e04_t9_fixture::silicon);const auto member=live.experiments.front();
        edi::Edit::peak_profile(*member,token)();
        CHECK_MESSAGE(edi::effective_peak_type(*member)==token,"EXPERIMENT648 ordinary TOF selector preserves exact long/control/UTF8 token; no computed-kernel claim");
        auto cw=edi::load_project(e04_t9_fixture::echidna);const auto before=edi::project_edi_files(cw);
        bool refused=false;try{edi::Edit::peak_profile(cw.experiment(),token)();}catch(const std::invalid_argument&){refused=true;}
        CHECK_MESSAGE((refused&&edi::project_edi_files(cw)==before),"EXPERIMENT648 offered TOF extension remains wrong-mode for genuine CW member");
    }
}

TEST_CASE("E11-T5 ordinary scalar absorption and cutoff weight restore retain scientific owners") {
    auto live=edi::load_project(e04_t9_fixture::echidna);
    const auto experiment=live.experiments.front();const auto structure=live.structures.front();
    REQUIRE_MESSAGE(experiment->data.has_value(),"SCALAR698 fixture is genuinely measured CW input");
    const auto* data=&*experiment->data;
    edi::Edit::absorption(*experiment,"cylinder-hewat")();
    REQUIRE(experiment->absorption.mu_r.has_value());
    auto* shared=&*experiment->absorption.mu_r;
    edi::Edit::value(*shared,.375)();shared->free=true;shared->uncertainty=.0125;
    const auto before=edi::project_edi_files(live);
    auto family=edi::capture_experiment_scalar(live,*experiment,edi::ExperimentScalarControl::Absorption);
    edi::Edit::absorption(*experiment,"cylinder-lobanov")();
    CHECK_MESSAGE((experiment->absorption.type=="cylinder-lobanov"&&experiment->absorption.mu_r.has_value()&&&*experiment->absorption.mu_r==shared),
        "SCALAR698 family forward transfer preserves the surviving actual coefficient handle");
    CHECK_MESSAGE((shared->value.get()==.375&&shared->free.get()&&shared->uncertainty.get()==std::optional<double>{.0125}),
        "SCALAR698 original coefficient value/free/SU survive an ordinary family change");
    edi::Edit::restore_experiment_controls(live,std::move(family))();
    CHECK_MESSAGE((edi::project_edi_files(live)==before&&&*experiment->absorption.mu_r==shared),
        "SCALAR698 ordinary family Undo restores all scientific bytes and surviving identity");
    auto removed=edi::capture_experiment_scalar(live,*experiment,edi::ExperimentScalarControl::Absorption);
    edi::Edit::absorption(*experiment,"none")();
    CHECK_MESSAGE((!experiment->absorption.mu_r.has_value()&&!experiment->absorption.abscor1.has_value()&&!experiment->absorption.abscor2.has_value()),
        "SCALAR698 none removes the actual optional coefficient owners");
    const auto empty=edi::project_edi_files(live);
    CHECK_MESSAGE((shared->is_detached()&&!shared->is_attached()&&shared->value.get()==.375&&shared->free.get()&&shared->uncertainty.get()==std::optional<double>{.0125}),
        "SCALAR743 retired native storage stays readable, detached and retains its original free/SU state");
    // Raw Edit::value is a range-checked native assignment, not the guarded Python handle setter.
    edi::Edit::value(*shared,.875)();
    CHECK_MESSAGE((shared->is_detached()&&!shared->is_attached()&&shared->value.get()==.875&&shared->free.get()&&shared->uncertainty.get()==std::optional<double>{.0125}),
        "SCALAR743 a valid raw write reaches only the still-readable retired native cell");
    CHECK_MESSAGE((edi::project_edi_files(live)==empty&&!experiment->absorption.mu_r.has_value()&&!experiment->absorption.abscor1.has_value()&&!experiment->absorption.abscor2.has_value()),
        "SCALAR743 a historical native cell cannot mutate the live project or resurrect any removed coefficient");
    edi::Edit::restore_experiment_controls(live,std::move(removed))();
    REQUIRE(experiment->absorption.mu_r.has_value());
    CHECK_MESSAGE((edi::project_edi_files(live)==before&&&*experiment->absorption.mu_r!=shared),
        "SCALAR698 Undo restores scientific state without resurrecting a detached historical cell");
    auto* restored=&*experiment->absorption.mu_r;
    CHECK_MESSAGE((shared->is_detached()&&!shared->is_attached()&&!restored->is_detached()&&restored!=shared),
        "SCALAR743 Undo creates a distinct live coefficient and leaves the historical native cell detached");
    REQUIRE_MESSAGE((shared->value.get()==.875&&shared->value.get()!=.625),
        "SCALAR746 post-Undo escape starts at the established historical value and must actually change it");
    edi::Edit::value(*shared,.625)();
    CHECK_MESSAGE((shared->is_detached()&&shared->value.get()==.625&&shared->free.get()&&shared->uncertainty.get()==std::optional<double>{.0125}),
        "SCALAR743 the retired cell remains readable after Undo without acquiring current ownership");
    CHECK_MESSAGE((edi::project_edi_files(live)==before&&&*experiment->absorption.mu_r==restored&&restored->value.get()==.375&&restored->free.get()&&restored->uncertainty.get()==std::optional<double>{.0125}),
        "SCALAR743 raw historical writes cannot alter the replacement's identity/value/free/SU or any live scientific byte");
    for(double literal:{0.0,-2.5}) {
        auto cutoff=edi::capture_experiment_scalar(live,*experiment,edi::ExperimentScalarControl::CutoffFwhm);
        edi::Edit::assign(experiment->peak.cutoff_fwhm,literal)();
        CHECK_MESSAGE(experiment->peak.cutoff_fwhm==literal,"SCALAR698 nonpositive cutoff is stored literally, never clamped to an invented positive threshold");
        edi::Edit::restore_experiment_controls(live,std::move(cutoff))();
        CHECK_MESSAGE(edi::project_edi_files(live)==before,"SCALAR698 cutoff Undo preserves the entire original project");
    }
    auto zero=edi::load_project(e04_t9_fixture::echidna);
    auto negative=edi::load_project(e04_t9_fixture::echidna);
    edi::Edit::assign(zero.experiment().peak.cutoff_fwhm,0.0)();
    edi::Edit::assign(negative.experiment().peak.cutoff_fwhm,-2.5)();
    // ADR0073 section7: published rows retain the original inclusive exclusion union.
    // Derive expected membership from SOURCE axis/intervals before either calculation, never its output.
    const auto axis=zero.experiment().data->axis();
    const auto observations=zero.experiment().data->intensity_meas.get();
    const auto sigmas=zero.experiment().data->intensity_meas_su.get();
    std::vector<std::pair<double,double>> intervals;
    for(const auto& region:zero.experiment().excluded_regions)
        intervals.emplace_back(region->first.get(),region->second.get());
    REQUIRE_MESSAGE((!axis.empty()&&observations.size()==axis.size()&&sigmas.size()==axis.size()),
        "SCALAR743 original complete measured rows and supplied sigmas define the independent mask axis");
    const auto negative_axis=negative.experiment().data->axis();
    std::vector<std::pair<double,double>> negative_intervals;
    for(const auto& region:negative.experiment().excluded_regions)
        negative_intervals.emplace_back(region->first.get(),region->second.get());
    REQUIRE_MESSAGE((negative_axis==axis&&negative_intervals==intervals&&negative.experiment().data->intensity_meas.get()==observations&&negative.experiment().data->intensity_meas_su.get()==sigmas),
        "SCALAR743 both independently loaded original banks have the same complete source rows and literal intervals before calculation");
    const auto source_mask=[](const auto& source_axis,const auto& source_intervals) {
        std::vector<bool> mask;
        for(double x:source_axis) {
            REQUIRE_MESSAGE(std::isfinite(x),"SCALAR743 every original measured axis coordinate is finite");
            bool masked=false;
            for(const auto& bounds:source_intervals)
                masked=masked||((bounds.first<=x&&x<=bounds.second)||(bounds.second<=x&&x<=bounds.first));
            mask.push_back(masked);
        }
        return mask;
    };
    const auto excluded=source_mask(axis,intervals);
    const auto negative_excluded=source_mask(negative_axis,negative_intervals);
    REQUIRE_MESSAGE(excluded==negative_excluded,"SCALAR743 both source-derived inclusive masks agree before either calculation");
    std::size_t included_count=0,excluded_count=0;
    for(bool masked:excluded) {if(masked)++excluded_count;else ++included_count;}
    REQUIRE_MESSAGE((included_count>0&&excluded_count>0),
        "SCALAR743 unchanged original fixture genuinely exercises both included and excluded published rows");
    zero.calculate();negative.calculate();
    for(const auto* calculated:{&zero,&negative}) {
        const auto& bank=calculated->experiment();
        CHECK_MESSAGE((bank.data->axis()==axis&&bank.data->intensity_meas.get()==observations&&bank.data->intensity_meas_su.get()==sigmas),
            "SCALAR743 calculation retains every original measured row/order/value and supplied sigma");
        REQUIRE_MESSAGE(bank.excluded_regions.size()==intervals.size(),"SCALAR743 every original exclusion interval remains present");
        for(std::size_t index=0;index<intervals.size();++index) {
            CHECK_MESSAGE((bank.excluded_regions[index]->first.get()==intervals[index].first&&bank.excluded_regions[index]->second.get()==intervals[index].second),
                "SCALAR743 calculation retains original exclusion order and literal endpoints");
        }
    }
    const auto& full=zero.experiment().data->intensity_calc;
    const auto& signed_full=negative.experiment().data->intensity_calc;
    const auto& zero_status=zero.experiment().data->calc_status;
    const auto& negative_status=negative.experiment().data->calc_status;
    REQUIRE_MESSAGE((full.size()==axis.size()&&signed_full.size()==axis.size()&&zero_status.size()==axis.size()&&negative_status.size()==axis.size()),
        "SCALAR743 both complete calculated/status columns retain the entire original measured population");
    for(std::size_t row=0;row<axis.size();++row) {
        const std::string expected=excluded[row]?"excl":"incl";
        CHECK_MESSAGE(zero_status[row]==expected,"SCALAR743 zero-cutoff published status matches the independent inclusive source mask");
        CHECK_MESSAGE(negative_status[row]==(negative_excluded[row]?"excl":"incl"),"SCALAR743 negative-cutoff published status matches its independent inclusive source mask");
        if(excluded[row]) {
            CHECK_MESSAGE((std::isnan(full[row])&&std::isnan(signed_full[row])),
                "SCALAR743 excluded published rows remain explicitly NaN, never infinity/zero/dropped rows");
        }else {
            REQUIRE_MESSAGE((std::isfinite(full[row])&&std::isfinite(signed_full[row])),
                "SCALAR743 every independently included published row is finite in both calculations");
            CHECK_MESSAGE(std::bit_cast<std::uint64_t>(full[row])==std::bit_cast<std::uint64_t>(signed_full[row]),
                "SCALAR698 zero and negative cutoff have the same original full-window semantics; no invented optimum or tolerance");
        }
    }
    auto weight=edi::capture_experiment_scalar(live,*experiment,edi::ExperimentScalarControl::DatasetWeight);
    edi::Edit::assign(experiment->dataset_weight,.625)();
    CHECK_MESSAGE(experiment->dataset_weight==.625,"SCALAR698 ordinary dataset weight stores the requested scalar; no single-bank curve claim");
    edi::Edit::restore_experiment_controls(live,std::move(weight))();
    CHECK_MESSAGE((edi::project_edi_files(live)==before&&live.experiments.front()==experiment&&live.structures.front()==structure&&&*experiment->data==data),
        "SCALAR698 scalar history preserves all original owners, data, observations, links, free flags and SUs");
}

TEST_CASE("E11-T5 ordinary phase links restore narrow science and pin actual appended rows") {
    using Result=edi::Edit::AppliedResult;
    static_assert(std::is_same_v<decltype(Result{}.linked_structure),const edi::LinkedStructure*>);
    auto live=edi::load_project(e04_t9_fixture::echidna);
    const auto experiment=live.experiments.front();const auto original_structure=live.structures.front();
    REQUIRE_MESSAGE((!experiment->linked_structures.empty()&&experiment->data.has_value()),
        "PHASE709 original measured project has a real initial link, never a fabricated empty bank");
    const auto initial_id=experiment->linked_structures.front()->structure_id.value();
    const auto initial_count=experiment->linked_structures.size();
    for(const auto* id:{"phase709_b","phase709_c"}) {
        auto extra=*original_structure;extra.name=id;edi::Edit::add_structure(live,std::move(extra))();
    }
    REQUIRE_MESSAGE((experiment->linked_structures.size()==initial_count&&experiment->linked_structures.front()->structure_id==initial_id),
        "PHASE709 ordinary independent structure setup preserves every real initial experiment link");
    auto row=experiment->linked_structures.front();
    edi::Edit::value(row->scale,.375)();row->scale.free=true;row->scale.uncertainty=.0125;
    const auto baseline=edi::project_edi_files(live);
    {
        auto history=edi::capture_experiment_links(live,*experiment);
        auto* scale=&row->scale;const auto link=row;
        edi::Edit::link_structure(*row,"phase709_b")();
        CHECK_MESSAGE((experiment->linked_structures.front()==link&&&link->scale==scale&&link->structure_id=="phase709_b"),
            "PHASE709 forward ordinary retarget retains actual link and scale owners");
        CHECK_MESSAGE((scale->value.get()==.375&&scale->free.get()&&scale->uncertainty.get()==std::optional<double>{.0125}),
            "PHASE709 retarget retains independently supplied scale value/free/SU");
        edi::Edit::restore_experiment_controls(live,std::move(history))();
        CHECK_MESSAGE(edi::project_edi_files(live)==baseline,"PHASE709 ordinary shared Undo restores all narrow rows, relations, scientific state and any existing fit state");
        row=experiment->linked_structures.front(); // Undo may retire old link/parameter handles.
    }
    {
        auto history=edi::capture_experiment_links(live,*experiment);
        edi::Edit::assign(row->enabled,false)();
        CHECK_MESSAGE((!row->enabled.get()&&row->structure_id==initial_id&&row->scale.value.get()==.375),
            "PHASE709 explicit false keeps the stored original row and its scale, not an inverted guess");
        edi::Edit::restore_experiment_controls(live,std::move(history))();
        CHECK_MESSAGE(edi::project_edi_files(live)==baseline,"PHASE709 enabled-state Undo restores all original scientific bytes");
        row=experiment->linked_structures.front();
    }
    {
        auto history=edi::capture_experiment_links(live,*experiment);
        edi::LinkedStructure extra;extra.structure_id="phase709_b";
        auto operation=edi::Edit::append(experiment->linked_structures,std::move(extra));
        bool applied=false;Result result{};int inputs=0,applied_events=0,edited=0;
        e04_t9::OwnerQueue queue;
        edi::work::Worker worker([&](auto delivery){queue.post(std::move(delivery));},{{},[&](const edi::work::Event& event){
            if(event.kind==edi::work::EventKind::Input){++inputs;
                CHECK_MESSAGE((!applied&&result.linked_structure==nullptr&&edi::project_edi_files(live)==baseline),
                    "PHASE709 original Input precedes append and clears the phase identity");}
            if(event.kind==edi::work::EventKind::Applied){++applied_events;
                CHECK_MESSAGE((applied&&experiment->linked_structures.size()==initial_count+1&&result.linked_structure==experiment->linked_structures.back().get()),
                    "PHASE709 actual inserted phase is pinned BEFORE the original fallible Applied publication");}
        }});
        edi::LivePreview preview(live,worker,{[&]{++edited;
            CHECK_MESSAGE((applied&&result.linked_structure==experiment->linked_structures.back().get()),
                "PHASE709 original edited callback sees the same actual early phase identity");
            throw std::runtime_error("phase709 original edited observer");},{}});
        bool intended=false;
        try{preview.apply(operation,&applied,&result);}catch(const std::runtime_error& error){intended=std::string(error.what())=="phase709 original edited observer";}
        REQUIRE_MESSAGE((intended&&inputs==1&&applied_events==1&&edited==1),
            "PHASE709 reaches the actual original post-apply failure exactly once, never an earlier admission/setup failure");
        REQUIRE_MESSAGE(experiment->linked_structures.size()==initial_count+1,"PHASE709 original append changes exactly one actual stored row");
        const auto inserted=experiment->linked_structures.back();
        CHECK_MESSAGE((result.linked_structure==inserted.get()&&result.linked_structure!=row.get()),
            "PHASE709 AppliedResult pins the actual newly inserted phase, never the preexisting initial link");
        CHECK_MESSAGE((inserted->structure_id=="phase709_b"&&inserted->scale.value.get()==1&&inserted->enabled.get()),
            "PHASE709 original ordinary append defaults are independent scale1 and enabled true");
        CHECK_MESSAGE((experiment->linked_structures.front()==row&&row->structure_id==initial_id&&row->scale.value.get()==.375),
            "PHASE709 append never overwrites the real initial link or scale");
        const auto appended=edi::project_edi_files(live);
        auto removal=edi::capture_experiment_links(live,*experiment);
        const auto removed_id=inserted->structure_id.value();
        edi::Edit::erase(experiment->linked_structures,experiment->linked_structures.size()-1)();
        CHECK_MESSAGE((experiment->linked_structures.size()==initial_count&&removed_id=="phase709_b"),
            "PHASE709 erase confirms the previously admitted ID without dereferencing an erased row");
        edi::Edit::restore_experiment_controls(live,std::move(removal))();
        CHECK_MESSAGE(edi::project_edi_files(live)==appended,"PHASE709 remove Undo restores complete ordered narrow row and scientific image");
        edi::Edit::restore_experiment_controls(live,std::move(history))();
        CHECK_MESSAGE(edi::project_edi_files(live)==baseline,"PHASE709 append Undo restores original science after reacquiring current rows");
        row=experiment->linked_structures.front();
    }
    CHECK_MESSAGE((row->structure_id==initial_id&&row->scale.value.get()==.375&&row->scale.free.get()&&row->scale.uncertainty.get()==std::optional<double>{.0125}),
        "PHASE709 current reacquired original link retains every independently supplied scale fact");
}

#else
#define E04_T9_RED(name) TEST_CASE(name) { FAIL_CHECK(" accepted worker and transaction contracts are absent on red-first main"); }
E04_T9_RED(" I2 I3 I4 I5 worker preserves every ordered delivery and cancellation")
E04_T9_RED(" worker destruction suppresses queued deliveries and cancels all tokens")
E04_T9_RED(" C1 C2 C3 C4 C7 C8 newest previews and independent ordered stream")
E04_T9_RED(" I12 I13 transaction stamps every bank structure membership and editor")
E04_T9_RED(" I13a publication is byte-equivalent to the retained direct calculation")
E04_T9_RED(" I1a registration refuses while any worker exists")
E04_T9_RED(" C5 newest refusal clears all computed categories without dropping final position")
#endif
