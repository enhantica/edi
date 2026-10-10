#include <crysta/analysis.hpp>
#include <crysta/fit_report.hpp>
#include <crysta/model.hpp>

#include <iomanip>
#include <iostream>
#include <stdexcept>

int main(int argc, char** argv) {
    if (argc != 2) throw std::invalid_argument("native conditioning requires one project");
    auto project = crysta::load_project(argv[1]);
    auto result = crysta::fit_project(project);
    if (!result.converged || result.covariance.empty())
        throw std::runtime_error("native conditioning requires a converged covariance");
    std::cout << std::setprecision(17) << "{\"n_data\":" << crysta::loaded_points(project)
              << ",\"reduced_chi_square\":" << result.reduced_chi_square
              << ",\"iterations\":" << result.iterations << ",\"labels\":[";
    for (std::size_t j = 0; j < result.covariance_labels.size(); ++j) {
        if (j) std::cout << ',';
        std::cout << std::quoted(result.covariance_labels[j]);
    }
    std::cout << "],\"values\":[";
    for (std::size_t j = 0; j < result.covariance_labels.size(); ++j) {
        if (j) std::cout << ',';
        std::cout << result.values.at(result.covariance_labels[j]);
    }
    std::cout << "],\"covariance\":[";
    for (std::size_t j = 0; j < result.covariance.size(); ++j) {
        if (j) std::cout << ',';
        std::cout << result.covariance[j];
    }
    std::cout << "]}\n";
}
