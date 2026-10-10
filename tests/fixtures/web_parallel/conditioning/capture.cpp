#include <crysta/analysis.hpp>
#include <crysta/fit_report.hpp>
#include <crysta/model.hpp>
#include <crysta/residual.hpp>

#include <iomanip>
#include <iostream>
#include <cmath>
#include <stdexcept>

int main(int argc, char** argv) {
    if (argc != 2) throw std::invalid_argument("native conditioning requires one project");
    auto project = crysta::load_project(argv[1]);
    auto result = crysta::fit_project(project);
    if (!result.converged || result.covariance.empty())
        throw std::runtime_error("native conditioning requires a converged covariance");
    crysta::PhaseSumResidual provider(project);
    if (provider.labels() != result.covariance_labels)
        throw std::runtime_error("native conditioning requires the same final free layout");
    std::cout << std::setprecision(17) << "{\"n_data\":" << provider.n_data()
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
    const auto jacobian = provider.jacobian(provider.values());
    const auto n = provider.n_free();
    std::cout << "],\"normal\":[";
    for (std::size_t j = 0; j < n; ++j) {
        for (std::size_t k = 0; k < n; ++k) {
            long double sum = 0;
            for (std::size_t row = 0; row < provider.n_data(); ++row) {
                const long double weight = std::sqrt(provider.weights()[row]);
                sum += (jacobian[row * n + j] * weight) * (jacobian[row * n + k] * weight);
            }
            if (j || k) std::cout << ',';
            std::cout << static_cast<double>(sum);
        }
    }
    std::cout << "]}\n";
}
