// Input carriers only: actual edi::new_atom_site executes unchanged.
#include <algorithm>
#include <array>
#include <cmath>
#include <functional>
#include <iostream>
#include <map>
#include <memory>
#include <string>
#include <vector>
struct Text {
    std::string text;
    const std::string& value() const { return text; }
    Text& operator=(const std::string& s) {
        text = s;
        return *this;
    }
};
struct Parameter {
    double value = 0;
};
struct AtomSite {
    Text id, type_symbol;
    std::string wyckoff_letter;
    Parameter fract_x, fract_y, fract_z;
};
struct Structure {
    std::vector<std::shared_ptr<AtomSite>> atom_sites;
};
namespace crysta {
struct SymmetryOperation {
    std::array<int, 9> rotation;
    std::array<double, 3> translation;
};
struct Position {
    int multiplicity;
};
struct SpaceGroup {
    std::map<std::string, Position> wyckoff;
};
std::vector<SymmetryOperation> operations;
std::vector<SymmetryOperation> symmetry_operations(const SpaceGroup&) { return operations; }
}  // namespace crysta
crysta::SpaceGroup resolve_group(const Structure&) { return {{{"a", {1}}, {"n", {48}}}}; }
const std::vector<std::string>& new_site_elements() {
    static const std::vector<std::string> supported{"H", "C", "O"};
    return supported;
}
// PRODUCTION_ATOM
int main() {
    int held, count;
    std::cin >> held;
    Structure structure;
    for (int i = 0; i < held; ++i) {
        auto atom = std::make_shared<AtomSite>();
        std::cin >> atom->id.text >> atom->type_symbol.text;
        structure.atom_sites.push_back(atom);
    }
    std::cin >> count;
    for (int i = 0; i < count; ++i) {
        crysta::SymmetryOperation op{};
        for (int& value : op.rotation) std::cin >> value;
        for (double& value : op.translation) std::cin >> value;
        crysta::operations.push_back(op);
    }
    std::vector<double> draws;
    double value;
    while (std::cin >> value) draws.push_back(value);
    std::size_t next = 0;
    try {
        auto atom = new_atom_site(structure, [&] {
            if (next == draws.size()) throw std::runtime_error("random stream exhausted");
            return draws[next++];
        });
        std::cout << atom.id.value() << ' ' << atom.type_symbol.value() << ' '
                  << atom.wyckoff_letter << ' ' << atom.fract_x.value << ' ' << atom.fract_y.value
                  << ' ' << atom.fract_z.value << ' ' << next << '\n';
    } catch (const std::exception& e) {
        std::cerr << e.what();
        return 1;
    }
}
