#include <algorithm>
#include <cmath>
#include <fstream>
#include <iostream>
#include <map>
#include <memory>
#include <optional>
#include <set>
#include <sstream>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

// This test-only translation unit includes the adapter implementation so it can mutate the V1
// boundary and inspect the persistent engine parameter. It never links edi_core, so no production
// definition is duplicated in the executable.
#define private public
#include "edi/model.hpp"
#undef private
#include "edi/io.hpp"
#include "../../../core/src/adapter.cpp"

namespace {

int require_v1_rejects_a_transposed_index(const std::string& fixture) {
    edi::Project model = edi::load_project(fixture);
    crysta::Project engine = edi::build_crysta_project(model.structure(), model.experiment());
    edi::make_fit_ready(engine.experiment());
    edi::Index index = edi::build_index(model, engine);
    std::swap(index.at("structure.cell.length_a").engine,
              index.at("structure.cell.length_b").engine);
    try {
        edi::validate_index(model, index, engine);
    } catch (const std::invalid_argument&) {
        return 0;
    }
    std::cerr << "V1 accepted an index with transposed engine slots\n";
    return 1;
}

}  // namespace

int main(int argc, char** argv) {
    if (argc < 3) return 2;
    const std::string mode = argv[1];
    if (mode == "v1" && argc == 3) return require_v1_rejects_a_transposed_index(argv[2]);
    return 2;
}
