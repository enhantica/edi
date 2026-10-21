#include <string>

#include "crysta/analysis.hpp"
#include "crysta/background_estimate.hpp"
#include "crysta/model.hpp"

int main(int argc, char** argv) {
    if (argc != 4) return 2;
    const std::string mode = argv[3];
    if (mode != "guided" && mode != "data-only" && mode != "calculate") return 2;
    auto project = crysta::load_project(argv[1]);
    crysta::calculate_project(project);
    if (mode == "guided") {
        crysta::BackgroundEstimateOptions options;
        options.method = "snip";
        options.width = 7.25;
        options.n_points = 9;
        options.use_model = true;
        crysta::auto_estimate_background(project.experiment(), options);
        crysta::calculate_project(project);
    }
    crysta::save_project(project, argv[2]);
}
