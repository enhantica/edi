#include <algorithm>
#include <bit>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <map>
#include <optional>
#include <sstream>
#include "e04_t9_support.hpp"

#if __has_include("edi/live_preview.hpp") && __has_include("edi/presentation.hpp")
#include "edi/live_preview.hpp"
#include "edi/presentation.hpp"
#include <crysta/analysis.hpp>
#include <crysta/computed.hpp>
#include <crysta/model.hpp>
#include "e04_t9_reference.hpp"

namespace {
struct Statistics { double median, p95; };
Statistics stats(std::vector<double> values) {
    std::sort(values.begin(), values.end());
    return {values[(values.size() + 1) / 2 - 1], values[static_cast<std::size_t>(std::ceil(.95 * values.size())) - 1]};
}
double maximum(const auto& values) {
    double result = -std::numeric_limits<double>::infinity();
    for (double value : values) if (std::isfinite(value)) result = std::max(result, value);
    return result;
}
void require(bool truth, const char* requirement) {
    if (!truth) throw std::runtime_error(requirement);
}
void json_stat(std::ostream& output, const char* name, const std::vector<double>& samples) {
    const auto s = stats(samples);
    output << std::quoted(name) << ":{\"median_ms\":" << s.median << ",\"p95_ms\":" << s.p95 << '}';
}
}  // namespace

int main(int argc, char** argv) {
    try {
        const std::string root = argc > 1 ? argv[1] : ".";
        const auto old = std::filesystem::current_path();
        std::filesystem::current_path(root);
        std::ostringstream table;
        const char* runner = std::getenv("RUNNER_NAME");
        const char* host = std::getenv("HOSTNAME");
        const char* commit = std::getenv("EDI_TEST_COMMIT");
        if (!commit) commit = std::getenv("GITHUB_SHA");
        table << std::setprecision(17) << "{\"schema\":1,\"machine\":"
              << std::quoted(runner ? runner : (std::string("hand:") + (host ? host : "unknown")).c_str())
              << ",\"commit\":" << std::quoted(commit ? commit : "unrecorded")
              << ",\"samples\":50,\"warmups\":5,\"rows\":[";
        bool comma = false;
        for (int dataset = 1; dataset <= 3; ++dataset) {
            const std::string path = dataset == 1 ? e04_t9_fixture::silicon : dataset == 2 ? e04_t9_fixture::wish : e04_t9_fixture::echidna;
            auto live = dataset == 3 ? e04_t9_fixture::stress() : edi::load_project(path);
            auto reference = crysta::load_project(path);
            if (dataset == 3) {
                reference.experiment().data.modify([&](auto& node) {
                    auto& data = *node;
                        data.grid.assign(live.experiment().data->axis());
                        data.intensity.assign(live.experiment().data->intensity_meas);
                        data.sigma.assign(live.experiment().data->intensity_meas_su);
                });
            }
            const double base = live.structure().cell.length_a.value;
            // Every requested state is independently calculated before the timed run.
            std::map<double, std::vector<double>> expected;
            for (int sample = 0; sample < 55; ++sample) {
                const double value = base + .0001 * (sample + 1);
                e04_t9::reference_length_a(reference, value);
                crysta::calculate_project(reference);
                for (const auto& bank : reference.experiments)
                    expected[value].push_back(maximum(crysta::current(reference, bank).data().intensity_calc));
            }
            for (int scenario = 1; scenario <= 3; ++scenario) {
                e04_t9::OwnerQueue queue;
                std::mutex trace_mutex;
                std::vector<edi::work::Event> trace;
                std::uint64_t start = 0, stop = 0, calc_begin = 0, calc_end = 0;
                std::mutex calc_mutex;
                std::vector<std::pair<std::uint64_t,std::uint64_t>> calc_times;
                double requested = base;
                edi::work::Worker worker([&](auto d) { queue.post(std::move(d)); },
                    {e04_t9::clock_ns, [&](const auto& e) { std::lock_guard lock(trace_mutex); trace.push_back(e); }});
                std::uint64_t observed_generation = 0;
                edi::LivePreview preview(live, worker, {[]{}, [&](const auto& result) {
                    require(live.structure().cell.length_a.value == requested,
                            " O2 completion requires the requested parameter state");
                    for (std::size_t b = 0; b < live.experiments.size(); ++b) {
                        require(live.experiments[b]->computed_current(), " O2 every bank must be current at completion");
                        const double actual = maximum(live.experiments[b]->data->intensity_calc);
                        const double wanted = expected.at(requested)[b];
                        if (actual != wanted) {
                            std::ostringstream error;
                            error << std::setprecision(17)
                                  << " O2 completion maximum must equal independently calculated crysta output: D"
                                  << dataset << " S" << scenario << " bank " << b << " requested " << requested
                                  << " actual " << actual << " expected " << wanted;
                            throw std::runtime_error(error.str());
                        }
                    }
                    observed_generation = result.generation;
                    stop = e04_t9::clock_ns();
                }}, {[&](auto& snapshot, const auto& token) {
                    calc_begin = e04_t9::clock_ns();
                    auto result = edi::calculate(snapshot, token);
                    calc_end = e04_t9::clock_ns();
                    { std::lock_guard lock(calc_mutex); calc_times.emplace_back(calc_begin, calc_end); }
                    return result;
                }});
                std::vector<double> latency, calculation, wait, overhead, presentation;
                for (int sample = 0; sample < 55; ++sample) {
                    requested = base + .0001 * (sample + 1);
                    stop = 0;
                    if (scenario < 3) {
                        { std::lock_guard lock(trace_mutex); trace.clear(); }
                        { std::lock_guard lock(calc_mutex); calc_times.clear(); }
                        start = e04_t9::clock_ns();
                        preview.apply(edi::Edit::value(live.structure().cell.length_a, requested));
                        if (scenario == 2) {
                            // Distinct immediate edits; no drain can publish an intermediate result.
                            preview.apply(edi::Edit::value(live.structure().cell.length_a, requested + .001));
                            start = e04_t9::clock_ns();
                            preview.apply(edi::Edit::value(live.structure().cell.length_a, requested));
                        }
                        double waited = 0;
                        if (scenario == 2) queue.one();
                        queue.one();
                        require(stop > start && observed_generation == preview.newest_request(),
                                " L10 only the final requested publication ends a timed sample");
                        const double total = (stop - start) / 1e6;
                        const double calc = (calc_end - calc_begin) / 1e6;
                        if (scenario == 2) {
                            std::lock_guard lock(calc_mutex);
                            require(calc_times.size() == 2, " L3 rapid requests perform one obsolete and one final calculation");
                            waited = static_cast<double>(calc_times.front().second > start ? calc_times.front().second - start : 0) / 1e6;
                        }
                        {
                            std::lock_guard lock(trace_mutex);
                            bool input = false, publication = false, calculating = false, calculated = false;
                            std::string endpoint_failures;
                            for (const auto& e : trace) if (e.id == observed_generation && e.channel == "preview") {
                                if (e.kind == edi::work::EventKind::Input) {
                                    input = true; require(e.at_ns >= start && e.at_ns <= stop, " O4 trace input must lie within the test-owned latency interval");
                                }
                                if (e.kind == edi::work::EventKind::Published) {
                                    publication = true; require(e.at_ns >= start && e.at_ns <= stop, " O4 trace publication must not certify an unrelated completion");
                                }
                                if (e.kind == edi::work::EventKind::Calculating) {
                                    calculating = true;
                                    if (e.at_ns < calc_begin || e.at_ns > calc_end)
                                        endpoint_failures += " start-outside";
                                }
                                if (e.kind == edi::work::EventKind::Calculated) {
                                    calculated = true;
                                    if (e.at_ns < calc_begin || e.at_ns > calc_end)
                                        endpoint_failures += " end-outside";
                                }
                            }
                            require(input && publication, " O4 measured request must have correlated input and publication traces");
                            require(calculating && calculated, " O4 each measured request must carry both calculation trace endpoints");
                            // Keep both independent endpoint checks; report both before refusing.
                            if (!endpoint_failures.empty())
                                throw std::runtime_error(" O4 calculation trace endpoints must lie inside the test-owned calculation interval:" + endpoint_failures);
                        }
                        if (sample >= 5) {
                            latency.push_back(total); calculation.push_back(calc); wait.push_back(waited);
                            overhead.push_back(total - waited - calc);
                        }
                    } else {
                        if (sample == 0) { preview.apply(edi::Edit::value(live.structure().cell.length_a, requested)); queue.one(); }
                        const auto source = edi::capture_pattern(live, 0);
                        edi::PatternView view; view.columns = 2400;
                        const auto& x = *source.x;
                        const double share = .1 + .001 * sample;
                        view.x_min = x.front() + share * (x.back() - x.front());
                        view.x_max = x.back() - share * (x.back() - x.front());
                        start = e04_t9::clock_ns();
                        const auto presented = edi::present_pattern(source, view);
                        stop = e04_t9::clock_ns();
                        require(presented.x.min == *view.x_min && presented.x.max == *view.x_max,
                                " O2 S3 completion requires the independently requested viewport");
                        if (sample >= 5) {
                            const double total = (stop - start) / 1e6;
                            latency.push_back(total); presentation.push_back(total); calculation.push_back(0);
                            wait.push_back(0); overhead.push_back(total);
                        }
                    }
                }
                if (comma) table << ',';
                comma = true;
                table << "{\"dataset\":\"D" << dataset << "\",\"scenario\":\"S" << scenario << "\",";
                json_stat(table,"latency",latency); table << ',';
                json_stat(table,"calculation",calculation); table << ',';
                json_stat(table,"wait",wait); table << ',';
                json_stat(table,"overhead",overhead);
                if (scenario == 3) { table << ','; json_stat(table,"presentation",presentation); }
                table << '}';
            }
        }
        table << "]}\n";
        std::filesystem::current_path(old);
        std::ofstream("latency-table.json") << table.str();
        std::cout << table.str();
        return 0;
    } catch (const std::exception& error) { std::cerr << error.what() << '\n'; return 1; }
}
#else
int main() { std::cerr << " latency probe requires the accepted live publication and presentation contracts\n"; return 1; }
#endif
