// SPDX-License-Identifier: BSD-3-Clause
#include "parameter_registry.hpp"

#include "edi/categories.hpp"
#include "edi/parameter_walk.hpp"
#include "parameter_item.hpp"
#include "project_editor.hpp"

namespace edi_app {

ParameterRegistry::ParameterRegistry(ProjectEditor& editor, QObject* parent) : QObject(parent), editor_(editor) {}

void ParameterRegistry::rebuild(edi::Project& project) {
    QList<ParameterItem*> items;
    std::map<std::pair<const edi::Parameter*, std::string>, ParameterItem*> by_key;
    // Each block's place in its list (edi ADR-0017 §8).
    std::map<std::string, int> structure_index, experiment_index;
    for (std::size_t i = 0; i < project.structures.size(); ++i) {
        structure_index.emplace(project.structures[i]->name, static_cast<int>(i));
    }
    for (std::size_t i = 0; i < project.experiments.size(); ++i) {
        experiment_index.emplace(project.experiments[i]->name, static_cast<int>(i));
    }
    for (const edi::ParameterEntry& entry : edi::parameter_entries(project)) {
        // A renamed block re-keys its items, so every constant an item carries stays true.
        const auto key = std::make_pair(static_cast<const edi::Parameter*>(entry.parameter),
                                        entry.path + '\n' + entry.block_name);
        auto found = by_key_.find(key);
        ParameterItem* item = nullptr;
        if (found != by_key_.end()) {
            item = found->second;
            by_key_.erase(found);
        } else {
            item = new ParameterItem(entry, editor_, this);
        }
        const auto& indices = entry.block_kind == "structure" ? structure_index : experiment_index;
        const auto place = indices.find(entry.block_name);
        item->setBlockIndex(place != indices.end() ? place->second : -1);
        item->setRefinable(entry.refinable);
        items.append(item);
        by_key.emplace(key, item);
    }
    const bool changed = !by_key_.empty() || items != items_;
    QList<ParameterItem*> removed;
    for (const auto& [key, item] : by_key_) {
        removed.append(item);
    }
    items_ = items;
    by_key_ = std::move(by_key);
    by_parameter_.clear();
    for (ParameterItem* item : items_) {
        by_parameter_.emplace(item->parameter(), item);
    }
    refreshElements(project);
    if (changed) {
        emit itemsChanged();
    }
    for (ParameterItem* item : removed) {
        item->deleteLater();
    }
}

void ParameterRegistry::refreshElements(const edi::Project& project) {
    // An atom-site parameter's element is its site's type symbol (edi ADR-0017 §8), which an edit changes
    // without changing the set of parameters: it is read again at every publish, never kept from a rebuild.
    std::unordered_map<const edi::Parameter*, std::string> element;
    for (const auto& structure : project.structures) {
        for (const auto& site : structure->atom_sites) {
            for (const edi::Parameter* parameter :
                 {&site->fract_x, &site->fract_y, &site->fract_z, &site->occupancy, &site->adp_iso}) {
                element.emplace(parameter, site->type_symbol);
            }
        }
    }
    // A phase's scale and texture take the colour of the structure they belong to, when there are several.
    std::unordered_map<const edi::Parameter*, int> phase;
    if (project.structures.size() > 1) {
        std::unordered_map<std::string, int> place;
        int index = 0;
        for (const auto& structure : project.structures) {
            place.emplace(structure->name.value(), index++);
        }
        const auto owned = [&](const edi::ItemKey& structure_id, const edi::Parameter* parameter) {
            const auto found = place.find(structure_id.value());
            if (found != place.end()) {
                phase.emplace(parameter, found->second);
            }
        };
        for (const auto& experiment : project.experiments) {
            for (const auto& link : experiment->linked_structures) {
                owned(link->structure_id, &link->scale);
            }
            for (const auto& row : experiment->preferred_orientation) {
                owned(row->structure_id, &row->march_r);
                owned(row->structure_id, &row->march_random_fract);
            }
        }
    }
    for (ParameterItem* item : items_) {
        const auto site = element.find(item->parameter());
        item->setElementSymbol(site != element.end() ? QString::fromStdString(site->second) : QString());
        const auto owner = phase.find(item->parameter());
        item->setPhaseIndex(owner != phase.end() ? owner->second : -1);
    }
}

void ParameterRegistry::refreshRefinable(edi::Project& project) {
    // What the space group leaves refinable (edi ADR-0019) follows an edit of the space group or of a
    // site's Wyckoff position, which changes no set of parameters: it is read again at every publish, from
    // the categories the walk itself reads, so the two never disagree.
    std::unordered_map<const edi::Parameter*, bool> refinable;
    for (const auto& structure : project.structures) {
        for (const edi::Category& category : edi::structure_categories(*structure)) {
            for (const edi::CategoryField& field : category.fields) {
                refinable.emplace(field.parameter, field.refinable);
            }
        }
    }
    for (ParameterItem* item : items_) {
        const auto found = refinable.find(item->parameter());
        item->setRefinable(found == refinable.end() || found->second);
    }
}

void ParameterRegistry::publish(edi::Project& project) {
    refreshElements(project);
    refreshRefinable(project);
    for (ParameterItem* item : items_) {
        item->publish();
    }
}

ParameterItem* ParameterRegistry::find(const edi::Parameter* parameter) const {
    const auto found = by_parameter_.find(parameter);
    return found != by_parameter_.end() ? found->second : nullptr;
}

QVariant parameter_role(const ParameterRegistry& registry, const void* parameter) {
    return QVariant::fromValue(
        static_cast<QObject*>(registry.find(static_cast<const edi::Parameter*>(parameter))));
}

}  // namespace edi_app
