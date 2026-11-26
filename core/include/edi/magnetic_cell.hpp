#pragma once

// The magnetic popup's engine calls (edi ADR-0078, "The magnetic popup"; crysta ADR-0137): the
// preset propagation vectors, the graph of the magnetic groups a propagation vector allows, and
// the candidate structures added from it. crysta computes everything; edi only converts.

#include <array>
#include <cstddef>
#include <memory>
#include <string>
#include <vector>

#include "edi/model.hpp"

namespace edi {

struct MagneticPreset {
    std::string k;      ///< `1/2,0,0`
    std::string label;  ///< `X`, or empty
};
/// The preset k list of a Crystal structure, k = 0 first.
std::vector<MagneticPreset> magnetic_presets(const Structure& parent);

/// The parent's sites whose element has a magnetic form factor: the popup ticks them by default.
std::vector<std::string> magnetic_default_sites(const Structure& parent);

struct MagneticCandidateNode {
    std::string bns;            ///< `62.452`, empty when not identified
    std::string name;           ///< `P_cnma`
    int type = 0;               ///< 1, 3 or 4
    int row = 1;                ///< 1: maximal among the moment-allowing groups
    std::size_t embedding = 1;  ///< `#n` among the nodes with this BNS number
    std::size_t domains = 1;
    bool net_moment = false;
    bool moment_allowed = true;
    std::vector<std::size_t> subgroups;  ///< covering edges
    std::string transform_to_bns;
    std::string moments;  ///< per ticked site, `Mn1_1 Mx,My,Mz · Mn2 0,0,Mz`
};
struct MagneticEngineGraph;  // crysta's graph and the parent it was built from (adapter.cpp)
struct MagneticCandidateGraph {
    std::string cell;  ///< `2a,b,c;0,0,0`
    long long parent_cells = 1;
    std::vector<MagneticCandidateNode> nodes;
    std::vector<std::string> sites;  ///< the ticked sites it was built for
    std::shared_ptr<const MagneticEngineGraph> engine;
};
/// The k-compatible magnetic groups of `parent` (crysta::magnetic_subgroups); it takes seconds for
/// a large group, so the app calls it off the GUI thread on a copy of the parent. Throws
/// std::invalid_argument with crysta's one message for a k it does not build.
MagneticCandidateGraph magnetic_candidate_graph(const Structure& parent, const std::string& k,
                                                const std::vector<std::string>& sites,
                                                bool with_zero_moment_groups);

/// One node's allowed moment components per magnetic site, `Mn1_1 Mx,My,Mz · Mn2 0,0,Mz`.
/// Safe to call off the GUI thread: it reads only `graph`.
std::string magnetic_candidate_moments(const MagneticCandidateGraph& graph, std::size_t node);

/// Everything an Add changes, built and validated before anything is applied.
struct PreparedMagneticCandidates {
    std::string parent;
    std::vector<std::shared_ptr<Structure>> structures;
    struct Link {
        std::size_t experiment = 0;
        std::string structure;
        double scale = 1.0;
        bool enabled = false;
    };
    std::vector<Link> links;
    struct Texture {
        std::size_t experiment = 0;
        std::string structure;
        double march_r = 1.0;
        double march_random_fract = 0.0;
        bool march_r_free = false;
        bool march_random_fract_free = false;
        std::array<int, 3> axis{0, 0, 1};
    };
    std::vector<Texture> textures;
};
/// Builds the selected nodes' structures and their links and texture rows, all or none (edi
/// ADR-0078): each powder experiment linking the parent links every child at scale S/N², only the
/// first enabled, and the parent's link disabled; a March-Dollase row of the parent is carried
/// with its axis in the child's basis. Throws std::invalid_argument, naming the reason, when the
/// parent is linked to a single-crystal experiment, a texture axis cannot be carried, or a child
/// cannot be built. Nothing in `project` changes.
std::shared_ptr<PreparedMagneticCandidates> prepare_magnetic_candidates(
    const Project& project, std::size_t parent, const MagneticCandidateGraph& graph,
    const std::vector<std::size_t>& nodes, bool start_moments);

}  // namespace edi
