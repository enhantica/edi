// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <algorithm>
#include <cstddef>
#include <memory>
#include <string>
#include <vector>

#include "edi/model.hpp"
#include "edi/validation.hpp"

// The R15 collection protocol's binding-plane view structs. A view is a borrowed descriptor
// over ONE live ItemVec inside its owning model object — never a snapshot: every operation
// resolves the live vector through the owner at call time. Lifetime is the binding layer's
// contract: the Python wrapper of a view keeps its owner's wrapper alive via
// nb::keep_alive<0,1> at the returning property, and each query iterator keeps its view alive
// the same way; items ride shared_ptr, so they carry their own lifetime. These are struct
// DEFINITIONS only — registration (and every nb::class_ option, including the four item
// classes' nb::is_weak_referenceable extras) lives in bindings.cpp.

namespace edi::views {

template <typename Owner, typename T, typename KeyClass>
struct KeyedView;

// The default admission rule of a keyed collection: every item is admitted.
template <typename Owner, typename T, typename KeyClass>
void validate_insert(const KeyedView<Owner, T, KeyClass>& /*view*/, const T& /*item*/) {}

// Keyed collection view (structures/name, experiments/name, atom_sites/id). KeyClass is the
// class the key field is declared on (ExperimentBase for BraggPdExperiment).
template <typename Owner, typename T, typename KeyClass>
struct KeyedView {
    Owner* owner;
    ItemVec<T> Owner::* member;
    ItemKey KeyClass::* key;  // The id the collection owns (ADR-0016)

    ItemVec<T>& vec() const { return owner->*member; }
    const std::string& key_of(const T& item) const { return (item.*key).value(); }

    // String lookup resolves the LAST match (the anchor's `_rebuild_index` dict overwrite —
    // plan seam row 2's composition rule); mutation verbs use find_first below.
    std::ptrdiff_t find_last(const std::string& name) const {
        const ItemVec<T>& items = vec();
        for (std::ptrdiff_t i = static_cast<std::ptrdiff_t>(items.size()) - 1; i >= 0; --i) {
            if (key_of(*items[static_cast<std::size_t>(i)]) == name) return i;
        }
        return -1;
    }
    // `add`-replacement and `remove` act on the FIRST match (the anchor's
    // `__setitem__`/`__delitem__` front scans).
    std::ptrdiff_t find_first(const std::string& name) const {
        const ItemVec<T>& items = vec();
        for (std::size_t i = 0; i < items.size(); ++i) {
            if (key_of(*items[i]) == name) return static_cast<std::ptrdiff_t>(i);
        }
        return -1;
    }
    // Insert-or-replace under `name` (upstream `__setitem__`): replace the item with the same
    // canonical key IN PLACE, else append. Both go through the collection's own admission — the
    // ids stay unique, and an item another collection holds is refused.
    void set_item(const std::string& name, std::shared_ptr<T> item) {
        validate_insert(*this, *item);  // per-collection admission (ADL; a no-op by default)
        const std::string wanted = KeyTraits<T>::canonical(name);
        ItemVec<T>& items = vec();
        for (std::size_t i = 0; i < items.size(); ++i) {
            if (KeyTraits<T>::canonical(key_of(*items[i])) == wanted) {
                items.replace_at(i, std::move(item));
                return;
            }
        }
        items.push_back(std::move(item));
    }
};

using StructuresView = KeyedView<Project, Structure, Structure>;
using ExperimentsView = KeyedView<Project, BraggPdExperiment, ExperimentBase>;
using AtomSitesView = KeyedView<Structure, AtomSite, AtomSite>;
using PrefOrientsView = KeyedView<ExperimentBase, PrefOrient, PrefOrient>;
using LinkedStructuresView = KeyedView<ExperimentBase, LinkedStructure, LinkedStructure>;

// A texture row is admitted only when its key names one of the experiment's linked structures
// (the loader's rule), before it is installed; one link without an id admits any key.
inline void validate_insert(const PrefOrientsView& view, const PrefOrient& row) {
    const ItemVec<LinkedStructure>& links = view.owner->linked_structures;
    const bool one_unnamed = links.size() == 1 && links.front()->structure_id.empty();
    const bool named = std::any_of(links.begin(), links.end(), [&](const auto& link) {
        return link->structure_id.value() == row.structure_id.value();
    });
    const std::string linked = links.size() == 1 ? links.front()->structure_id.value() : std::string();
    for (const int index : {row.index_h, row.index_k, row.index_l}) {
        if (index > kPreferredOrientationAxisBound || index < -kPreferredOrientationAxisBound) {
            fail_domain("experiment '" + view.owner->name + "'", "preferred-orientation-domain",
                        "a texture axis component exceeds the Miller-index bound " +
                            std::to_string(kPreferredOrientationAxisBound));  // review-4 F2
        }
    }
    if (row.structure_id.empty() || (!one_unnamed && !named)) {
        fail_domain("experiment '" + view.owner->name + "'", "preferred-orientation-structure",
                    "_preferred_orientation.structure_id '" + row.structure_id +
                        "' does not name the linked structure '" + linked + "'");
    }
}

// Lazy query iterator over the live storage (plan seam row 5): index-based and bounds-checked at
// every step, so it is well-defined under mutation like upstream's generators and never
// dereferences a stale position. Carries no Python state — the keep_alive chain to the view is
// installed at the binding.
enum class IterMode { Keys, Values, Items };

template <typename Owner, typename T, typename KeyClass>
struct KeyedIter {
    KeyedView<Owner, T, KeyClass> view;
    IterMode mode;
    std::size_t index = 0;
};

using StructuresIter = KeyedIter<Project, Structure, Structure>;
using ExperimentsIter = KeyedIter<Project, BraggPdExperiment, ExperimentBase>;
using AtomSitesIter = KeyedIter<Structure, AtomSite, AtomSite>;
using PrefOrientsIter = KeyedIter<ExperimentBase, PrefOrient, PrefOrient>;
using LinkedStructuresIter = KeyedIter<ExperimentBase, LinkedStructure, LinkedStructure>;

// Positional live view over the background (R12 committed `id` -> list position, so it is not a
// keyed category; internal-only registration).
struct BackgroundView {
    ExperimentBase* experiment;
    ItemVec<LineSegment>& vec() const { return experiment->background; }
};

struct BackgroundIter {
    ExperimentBase* experiment;
    std::size_t index = 0;
};

}  // namespace edi::views
