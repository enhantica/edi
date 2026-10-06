// SPDX-License-Identifier: BSD-3-Clause
#include "adp_preview.hpp"

#include <algorithm>
#include <cmath>

namespace edi_app {

namespace {

constexpr double kPi = 3.141592653589793238;
constexpr double kTwoPiSq = 2.0 * kPi * kPi;
constexpr double kEightPiSq = 8.0 * kPi * kPi;
constexpr int kRow[6] = {0, 1, 2, 0, 0, 1};
constexpr int kColumn[6] = {0, 1, 2, 1, 2, 2};

using Matrix = std::array<std::array<double, 3>, 3>;

Matrix direct_metric(const AdpCell& cell) {
    const double radians = kPi / 180.0;
    const double ca = std::cos(cell.alpha * radians);
    const double cb = std::cos(cell.beta * radians);
    const double cg = std::cos(cell.gamma * radians);
    return {{{cell.a * cell.a, cell.a * cell.b * cg, cell.a * cell.c * cb},
             {cell.a * cell.b * cg, cell.b * cell.b, cell.b * cell.c * ca},
             {cell.a * cell.c * cb, cell.b * cell.c * ca, cell.c * cell.c}}};
}

Matrix inverse(const Matrix& m) {
    const double det = m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1]) -
                       m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0]) +
                       m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]);
    Matrix out{};
    for (int i = 0; i < 3; ++i) {
        for (int j = 0; j < 3; ++j) {
            const int i1 = (j + 1) % 3, i2 = (j + 2) % 3, j1 = (i + 1) % 3, j2 = (i + 2) % 3;
            out[i][j] = (m[i1][j1] * m[i2][j2] - m[i1][j2] * m[i2][j1]) / det;
        }
    }
    return out;
}

struct Metric {
    Matrix direct, reciprocal;
    std::array<double, 3> star;  // a*, b*, c*
};

Metric metric_of(const AdpCell& cell) {
    Metric metric{direct_metric(cell), {}, {}};
    metric.reciprocal = inverse(metric.direct);
    for (int i = 0; i < 3; ++i) {
        metric.star[i] = std::sqrt(metric.reciprocal[i][i]);
    }
    return metric;
}

// The tensor as CIF U components, whatever its type.
AdpTensor to_u(const AdpTensor& tensor, const std::string& type, const Metric& metric) {
    AdpTensor u{};
    for (int k = 0; k < 6; ++k) {
        if (type == "Bani") {
            u[k] = tensor[k] / kEightPiSq;
        } else if (type == "beta") {
            u[k] = tensor[k] / (kTwoPiSq * metric.star[kRow[k]] * metric.star[kColumn[k]]);
        } else {
            u[k] = tensor[k];
        }
    }
    return u;
}

// Components below this share of the largest are rounding left by the metric (cos 90 degrees is not 0 in
// floating point), shown as 0.
constexpr double kRoundingShare = 1e-12;

AdpTensor from_u(const AdpTensor& u, const std::string& type, const Metric& metric) {
    AdpTensor out{};
    for (int k = 0; k < 6; ++k) {
        if (type == "Bani") {
            out[k] = u[k] * kEightPiSq;
        } else if (type == "beta") {
            out[k] = u[k] * kTwoPiSq * metric.star[kRow[k]] * metric.star[kColumn[k]];
        } else {
            out[k] = u[k];
        }
    }
    double largest = 0.0;
    for (const double component : out) {
        largest = std::max(largest, std::abs(component));
    }
    for (double& component : out) {
        if (std::abs(component) < kRoundingShare * largest) {
            component = 0.0;
        }
    }
    return out;
}

}  // namespace

bool is_anisotropic(const std::string& type) { return type == "Bani" || type == "Uani" || type == "beta"; }

AdpTensor tensor_from_b_iso(const std::string& type, double b_iso, const AdpCell& cell) {
    const Metric metric = metric_of(cell);
    const double u_iso = b_iso / kEightPiSq;
    AdpTensor u{};
    for (int k = 0; k < 6; ++k) {
        const int i = kRow[k], j = kColumn[k];
        u[k] = u_iso * metric.reciprocal[i][j] / (metric.star[i] * metric.star[j]);
    }
    return from_u(u, type, metric);
}

AdpTensor convert_tensor(const AdpTensor& tensor, const std::string& from, const std::string& to,
                         const AdpCell& cell) {
    const Metric metric = metric_of(cell);
    return from_u(to_u(tensor, from, metric), to, metric);
}

double b_equivalent(const AdpTensor& tensor, const std::string& type, const AdpCell& cell) {
    const Metric metric = metric_of(cell);
    const AdpTensor u = to_u(tensor, type, metric);
    double sum = 0.0;
    for (int k = 0; k < 6; ++k) {
        const int i = kRow[k], j = kColumn[k];
        const double term = u[k] * metric.star[i] * metric.star[j] * metric.direct[i][j];
        sum += i == j ? term : 2.0 * term;
    }
    return kEightPiSq * sum / 3.0;
}

std::array<double, 9> cartesian_u(const AdpTensor& tensor, const std::string& type, const AdpCell& cell,
                                  const std::array<double, 9>& cartn_matrix) {
    const Metric metric = metric_of(cell);
    const AdpTensor u = to_u(tensor, type, metric);
    Matrix full{};
    for (int k = 0; k < 6; ++k) {
        const int i = kRow[k], j = kColumn[k];
        full[i][j] = full[j][i] = u[k] * metric.star[i] * metric.star[j];
    }
    // A (N U N) A^T, A taking fractional coordinates to Cartesian ones.
    Matrix half{};
    for (int i = 0; i < 3; ++i) {
        for (int j = 0; j < 3; ++j) {
            for (int k = 0; k < 3; ++k) {
                half[i][j] += cartn_matrix[3 * i + k] * full[k][j];
            }
        }
    }
    std::array<double, 9> out{};
    for (int i = 0; i < 3; ++i) {
        for (int j = 0; j < 3; ++j) {
            for (int k = 0; k < 3; ++k) {
                out[3 * i + j] += half[i][k] * cartn_matrix[3 * j + k];
            }
        }
    }
    return out;
}

}  // namespace edi_app
