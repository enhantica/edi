// M1-M6: clock the real capture/draw and edit/publication paths. No
// acceptance limit. The existing latency bank compares measured medians.
#include <crysta/model.hpp>
#include <crysta/structure_geometry.hpp>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>

#include "../../fixtures/e04_t10/generated.hpp"
#include "e04_t9_support.hpp"
#if __has_include("edi/structure_scene.hpp")
#include <bit>

#include "edi/live_preview.hpp"
#include "edi/structure_scene.hpp"
namespace {
void require(bool truth, const char* message) {
    if (!truth) throw std::runtime_error(message);
}
void statistic(std::ostream& out, const char* metric, std::vector<double> samples) {
    std::sort(samples.begin(), samples.end());
    out << std::quoted(metric) << ":{\"median_ms\":" << samples[24]
        << ",\"p95_ms\":" << samples[47] << '}';
}
bool same(double a, double b) {
    return std::bit_cast<std::uint64_t>(a) == std::bit_cast<std::uint64_t>(b);
}
}  // namespace
int main(int argc, char** argv) {
    std::string phase = "setup";
    try {
        const auto output_dir = std::filesystem::current_path();
        if (argc > 1) std::filesystem::current_path(argv[1]);
        const char *host = std::getenv("HOSTNAME"), *runner = std::getenv("RUNNER_NAME"),
                   *sha = std::getenv("EDI_TEST_COMMIT");
        if (!sha) sha = std::getenv("GITHUB_SHA");
        std::ostringstream out;
        out << std::setprecision(17) << "{\"schema\":1,\"machine\":"
            << std::quoted(runner ? std::string(runner)
                                  : std::string("hand:") + (host ? host : "unknown"))
            << ",\"commit\":" << std::quoted(sha ? sha : "unrecorded")
            << ",\"samples\":50,\"warmups\":5,\"rows\":[";
        bool comma = false;
        for (const bool large : {false, true}) {
            phase = large ? "G1 load" : "T1 load";
            auto live =
                large ? e04_t10_fixture::generated() : edi::load_project(e04_t10_fixture::t1);
            phase = large ? "G1 independent geometry" : "T1 independent geometry";
            auto reference = crysta::load_project(e04_t10_fixture::t1);
            if (large) {
                const auto generated =
                    crysta::structure_from_edi_text(e04_t10_fixture::generated_text());
                reference.structure() = generated;
                for (auto& bank : reference.experiments)
                    for (auto& link : bank.linked_structures) link.structure_id = generated.name;
            }
            phase = large ? "G1 current geometry" : "T1 current geometry";
            live.structure().current_geometry();
            const double base = live.structure().atom_sites[0]->fract_x.value;
            struct Expected {
                std::vector<double> x, y, z;
            };
            std::map<double, Expected> expected;
            phase = large ? "G1 independent requested states" : "T1 independent requested states";
            for (const double value : {base + .001, base + .002}) {
                reference.structure().atom_sites[0].fract[0].set_value(value);
                const auto& rows = crysta::current(reference.structure()).expanded_atom_sites;
                auto& e = expected[value];
                for (std::size_t i = 0; i < rows.size(); ++i) {
                    e.x.push_back(rows.cartn_x[i]);
                    e.y.push_back(rows.cartn_y[i]);
                    e.z.push_back(rows.cartn_z[i]);
                }
            }
            e04_t9::OwnerQueue queue;
            std::vector<double> latency, calculation, overhead, presentation;
            std::uint64_t start = 0, stop = 0, calc_ns = 0, generation = 0;
            double requested = base;
            edi::work::Worker worker([&](auto delivery) { queue.post(std::move(delivery)); });
            edi::LivePreview preview(
                live, worker,
                {[] {},
                 [&](const auto& result) {
                     require(live.structure().atom_sites[0]->fract_x.value == requested,
                             " M6 completion requires the requested final independent coordinate");
                     const auto source = edi::capture_scene(live.structure());
                     require(source.current && source.cartn_x,
                             " O2 completion requires current published geometry");
                     require(
                         expected.contains(requested),
                         " M6 requested input must be one of the independently prepared states");
                     const auto& e = expected.at(requested);
                     require(source.cartn_x->size() == e.x.size(),
                             " O2 independent final engine geometry has the same row count");
                     for (std::size_t r = 0; r < e.x.size(); ++r)
                         require(same((*source.cartn_x)[r], e.x[r]) &&
                                     same((*source.cartn_y)[r], e.y[r]) &&
                                     same((*source.cartn_z)[r], e.z[r]),
                                 " M6 completion sees the independent requested state rather than "
                                 "the previous frame");
                     const auto scene = edi::present_structure(source, {});
                     const auto drawing = edi::scene_drawing(scene, {1280, 768, 84});
                     require(!drawing.spheres.empty() || !drawing.shared.empty(),
                             " O2 completion actually prepares the renderer buffers");
                     generation = result.generation;
                     stop = e04_t9::clock_ns();
                 }},
                {[&](auto& snapshot, const auto& token) {
                    const auto begin = e04_t9::clock_ns();
                    auto result = edi::calculate(snapshot, token);
                    calc_ns = e04_t9::clock_ns() - begin;
                    return result;
                }});
            for (int sample = 0; sample < 55; ++sample) {
                const auto begin = e04_t9::clock_ns();
                const auto source = edi::capture_scene(live.structure());
                const auto scene = edi::present_structure(source, {});
                const auto drawing = edi::scene_drawing(scene, {1280, 768, 84});
                const auto done = e04_t9::clock_ns();
                require(scene.current && !drawing.spheres.empty(),
                        " V1 clocks actual capture presentation and drawing of current geometry");
                if (sample >= 5) presentation.push_back((done - begin) / 1e6);
                requested = base + .001 * (1 + sample % 2);
                stop = 0;
                calc_ns = 0;
                phase = (large ? "G1 edit/publication sample " : "T1 edit/publication sample ") +
                        std::to_string(sample);
                start = e04_t9::clock_ns();
                preview.apply(
                    edi::Edit::value(live.structure().atom_sites[0]->fract_x, requested));
                for (int n = 0; n < 8 && preview.busy(); ++n) queue.one();
                require(stop > start && generation == preview.newest_request(),
                        " O1 O2 stop follows real input and acknowledges the newest publication");
                require(calc_ns > 0 && stop - start >= calc_ns,
                        " O3 calculation interval lies inside the actual measured update");
                if (sample >= 5) {
                    latency.push_back((stop - start) / 1e6);
                    calculation.push_back(calc_ns / 1e6);
                    overhead.push_back((stop - start - calc_ns) / 1e6);
                }
            }
            for (const char* scenario : {"V1", "V2"}) {
                if (comma) out << ',';
                comma = true;
                out << "{\"dataset\":" << std::quoted(large ? "G1" : "T1")
                    << ",\"scenario\":" << std::quoted(scenario) << ',';
                if (std::string(scenario) == "V1")
                    statistic(out, "presentation", presentation);
                else {
                    statistic(out, "latency", latency);
                    out << ',';
                    statistic(out, "calculation", calculation);
                    out << ',';
                    statistic(out, "overhead", overhead);
                }
                out << '}';
            }
        }
        out << "]}\n";
        std::ofstream file(output_dir / "latency-table.json");
        require(bool(file), " M4 measurement output is writable");
        file << out.str();
        std::cout << out.str();
        return 0;
    } catch (const std::exception& error) {
        std::cerr << phase << ": " << error.what() << '\n';
        return 1;
    }
}
#else
int main() {
    std::cerr << " M2 structure scene API is not implemented\n";
    return 2;
}
#endif
