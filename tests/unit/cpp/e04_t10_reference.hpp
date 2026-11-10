#pragma once
#include <algorithm>
#include <array>
#include <cmath>
#include <fstream>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace e04_t10 {
struct PublishedElement {
    std::string symbol, jmol, vesta;
    double covalent, vdw;
    double ionic = -1;
};
inline std::vector<PublishedElement> elements() {
    std::ifstream file("tests/fixtures/e04_t10/published-elements.tsv");
    if (!file) throw std::runtime_error(" I6 independent published fixture is required");
    std::string line;
    std::getline(file, line);
    std::vector<PublishedElement> result;
    while (std::getline(file, line)) {
        std::vector<std::string> fields;
        std::size_t first = 0;
        for (;;) {
            auto last = line.find('\t', first);
            fields.push_back(line.substr(first, last - first));
            if (last == std::string::npos) break;
            first = last + 1;
        }
        if (fields.size() != 6) throw std::runtime_error(" I6 fixture requires six fields");
        result.push_back({fields[0], fields[1], fields[2], std::stod(fields[3]),
                          std::stod(fields[4]), fields[5].empty() ? -1 : std::stod(fields[5])});
    }
    return result;
}
using Vector = std::array<double, 3>;
inline Vector add(Vector a, Vector b) { return {a[0]+b[0], a[1]+b[1], a[2]+b[2]}; }
inline Vector times(Vector a, double k) { return {a[0]*k, a[1]*k, a[2]*k}; }
inline double dot(Vector a, Vector b) { return a[0]*b[0]+a[1]*b[1]+a[2]*b[2]; }
inline Vector cross(Vector a, Vector b) { return {a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]}; }
inline Vector unit(Vector a) { return times(a, 1/std::sqrt(dot(a,a))); }
struct Frame { Vector target, direction, up, right; double width, height; };
// Independent transcription of diffraction-lib's THREE.Vector3 formulas,
// not a call into edi's view helpers or a pin of their generated output.
inline Frame home(const std::array<Vector,3>& basis, std::vector<Vector> points, double pad) {
    auto sorted = basis;
    std::stable_sort(sorted.begin(), sorted.end(), [](auto a, auto b) { return dot(a,a)>dot(b,b); });
    const auto dir = unit(add(add(times(unit(sorted[0]),.37),times(unit(sorted[1]),.24)),times(unit(sorted[2]),.90)));
    const auto right = unit(cross(unit(sorted[1]), dir));
    const auto up = cross(dir,right);
    const auto centre = times(add(add(basis[0],basis[1]),basis[2]),.5);
    for (int i=0;i<2;++i) for (int j=0;j<2;++j) for (int k=0;k<2;++k)
        points.push_back(add(add(times(basis[0],i),times(basis[1],j)),times(basis[2],k)));
    double lo_u=INFINITY,hi_u=-INFINITY,lo_v=INFINITY,hi_v=-INFINITY;
    for(auto p:points) {
        const auto d=add(p,times(centre,-1));
        const auto u=dot(d,right),v=dot(d,up);
        lo_u=std::min(lo_u,u);hi_u=std::max(hi_u,u);
        lo_v=std::min(lo_v,v);hi_v=std::max(hi_v,v);
    }
    return {add(add(centre,times(right,(lo_u+hi_u)/2)),times(up,(lo_v+hi_v)/2)),
            dir,up,right,std::max((hi_u-lo_u)/2+pad,.5)*1.24,std::max((hi_v-lo_v)/2+pad,.5)*1.24};
}
}  // namespace e04_t10
