#include <doctest/doctest.h>
#include <atomic>
#include <bit>
#include <optional>
#include <thread>
#include <type_traits>
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
            using Apply = decltype(&edi::LivePreview::apply);
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
