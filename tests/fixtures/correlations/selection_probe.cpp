// Compile the unedited production rebuild method with container/signal carriers.
// This isolates matrix selection and masking; it is not a Qt host or wiring proof.
#include <algorithm>
#include <bit>
#include <cmath>
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <limits>
#include <string>
#include <vector>

struct QString : std::string {
    using std::string::string;
    static QString fromStdString(const std::string& text) { return QString(text.c_str()); }
};
template <typename T>
struct List : std::vector<T> {
    void append(const T& value) { this->push_back(value); }
};
using QStringList = List<QString>;
using qreal = double;
template <typename T>
using QList = List<T>;
#define emit
struct CorrelationViewModel {
    std::vector<std::string> names_;
    std::vector<double> matrix_, strength_;
    QString reason_, empty_text_;
    QStringList labels_;
    QList<qreal> values_;
    int available_ = 0, max_parameters_ = 3;
    double level_ = 0;
    static QString tr(const char* text) { return QString(text); }
    void valuesChanged() {}
    void labelsChanged() {}
    void availableChanged() {}
    void emptyTextChanged() {}
    void rebuild();
};
// PRODUCTION_REBUILD
int main(int argc, char** argv) {
    if (argc != 3) return 2;
    CorrelationViewModel model;
    model.level_ = std::stod(argv[1]);
    model.max_parameters_ = std::stoi(argv[2]);
    std::size_t n;
    std::cin >> n;
    for (std::size_t i = 0; i < n; ++i) {
        std::string name;
        std::cin >> name;
        model.names_.push_back(name);
    }
    for (std::size_t i = 0; i < n * n; ++i) {
        std::string value;
        std::cin >> value;
        model.matrix_.push_back(std::stod(value));
    }
    model.strength_.assign(n, 0);
    for (std::size_t i = 0; i < n; ++i)
        for (std::size_t j = 0; j < n; ++j) {
            const double value = model.matrix_[i * n + j];
            if (i != j && std::isfinite(value))
                model.strength_[i] = std::max(model.strength_[i], std::abs(value));
        }
    model.rebuild();
    std::cout << model.labels_.size() << '\n';
    for (const auto& name : model.labels_) std::cout << name << '\n';
    std::cout << std::setprecision(17);
    for (double value : model.values_) std::cout << value << '\n';
}
