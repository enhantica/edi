#include <cmath>
#include <locale>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

namespace {

class CommaDecimal final : public std::numpunct<char> {
   protected:
    char do_decimal_point() const override { return ','; }
};

bool parse_with(const std::string& token, const std::locale& locale, double& value) {
    std::istringstream stream(token);
    stream.imbue(locale);
    stream >> value;
    return !stream.fail() && stream.eof() && std::isfinite(value);
}

void require(bool condition, const std::string& message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

}  // namespace

int main() {
    const std::locale comma(std::locale::classic(), new CommaDecimal);
    const std::locale previous = std::locale::global(comma);
    try {
        const std::vector<std::pair<std::string, double>> accepted = {
            {"449.2719", 449.2719}, {"7305.1274", 7305.1274}, {"-1.08308", -1.08308},
            {"2.5e3", 2500.0},     {"+1.5", 1.5},         {".5", 0.5},
            {"1.", 1.0},
        };
        for (const auto& [token, expected] : accepted) {
            double value = 0.0;
            require(parse_with(token, std::locale::classic(), value),
                    "classic parser rejected " + token);
            require(value == expected, "classic parser changed " + token);
        }
        for (const std::string& token : {"1.2(3)", "1e999", "nan", "0.1abc"}) {
            double value = 0.0;
            require(!parse_with(token, std::locale::classic(), value),
                    "classic parser accepted " + token);
        }

        double counterfactual = 0.0;
        require(!parse_with("449.2719", comma, counterfactual),
                "comma-decimal counterfactual consumed a dot-decimal token");
        require(counterfactual == 449.0,
                "comma-decimal counterfactual did not stop before the dot");

        double portable = 0.0;
        require(parse_with("449.2719", std::locale::classic(), portable),
                "explicit classic locale followed the injected process locale");
        require(portable == 449.2719, "explicit classic locale changed the value");
    } catch (...) {
        std::locale::global(previous);
        throw;
    }
    std::locale::global(previous);
    return 0;
}
