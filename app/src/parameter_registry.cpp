// SPDX-License-Identifier: BSD-3-Clause
#include "parameter_registry.hpp"

#include "edi/background_estimate.hpp"
#include "edi/categories.hpp"
#include "edi/display.hpp"
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
        item->setSuRule(project.su_rule);
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
    refreshEstimated(project);
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
    // Likewise an ADP parameter's symbol and units, which follow its site's declared type.
    std::unordered_map<const edi::Parameter*, std::string> element;
    // An ADP's label and units for its site's declared type, from the dictionary's variants.
    struct AdpLabel {
        std::string label;
        std::string units;
        std::string variant;
    };
    const auto adp_label = [](const char* uid, const std::string& type) {
        return AdpLabel{edi::label(uid, type), edi::units_label(uid, type), type};
    };
    std::unordered_map<const edi::Parameter*, AdpLabel> adp;
    for (const auto& structure : project.structures) {
        for (const auto& site : structure->atom_sites) {
            for (const edi::Parameter* parameter :
                 {&site->fract_x, &site->fract_y, &site->fract_z, &site->occupancy, &site->adp_iso}) {
                element.emplace(parameter, site->type_symbol);
            }
            adp.emplace(&site->adp_iso, adp_label("atom_site.adp_iso", site->adp_type.value()));
            for (const auto& tensor : structure->atom_site_aniso) {
                if (tensor->id.value() == site->id.value()) {
                    const char* const components[] = {"atom_site_aniso.adp_11", "atom_site_aniso.adp_22",
                                                      "atom_site_aniso.adp_33", "atom_site_aniso.adp_12",
                                                      "atom_site_aniso.adp_13", "atom_site_aniso.adp_23"};
                    const auto parameters = tensor->parameters();
                    for (std::size_t i = 0; i < parameters.size(); ++i) {
                        element.emplace(parameters[i], site->type_symbol);
                        adp.emplace(parameters[i], adp_label(components[i], site->adp_type.value()));
                    }
                }
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
        if (const auto label = adp.find(item->parameter()); label != adp.end()) {
            item->setLabel(QString::fromStdString(label->second.label),
                           QString::fromStdString(label->second.units));
            item->setVariant(QString::fromStdString(label->second.variant));
        }
    }
}

void ParameterRegistry::refreshRefinable(edi::Project& project) {
    // What the space group leaves refinable (edi ADR-0019) follows an edit of the space group or of a
    // site's Wyckoff position, which changes no set of parameters: it is read again at every publish, from
    // the categories the walk itself reads, so the two never disagree.
    // Every category the walk reads, experiments' too: an item missing here would turn refinable on the
    // next publish, so a live edit could add a parameter the table did not list before.
    std::unordered_map<const edi::Parameter*, bool> refinable;
    const auto note = [&refinable](const edi::Category& category) {
        for (const auto* fields : {&category.fields, &category.asymmetry}) {
            for (const edi::CategoryField& field : *fields) {
                refinable.emplace(field.parameter, field.refinable);
            }
        }
    };
    for (const auto& structure : project.structures) {
        for (const edi::Category& category : edi::structure_categories(*structure)) {
            note(category);
        }
    }
    for (const auto& experiment : project.experiments) {
        for (const edi::Category& category : edi::experiment_categories(*experiment)) {
            note(category);
        }
    }
    for (ParameterItem* item : items_) {
        const auto found = refinable.find(item->parameter());
        item->setRefinable(found == refinable.end() || found->second);
    }
}

void ParameterRegistry::refreshEstimated(const edi::Project& project) {
    // An auto-mode background's values (ADR-0040) follow its mode, which an edit changes without changing the set of
    // parameters.
    std::unordered_set<const edi::Parameter*> estimated;
    for (const auto& experiment : project.experiments) {
        for (const edi::Parameter* parameter : edi::estimated_background_values(*experiment)) {
            estimated.insert(parameter);
        }
    }
    for (ParameterItem* item : items_) {
        item->setEstimated(estimated.contains(item->parameter()));
    }
}

void ParameterRegistry::publish(edi::Project& project) {
    refreshElements(project);
    refreshRefinable(project);
    refreshEstimated(project);
    for (ParameterItem* item : items_) {
        item->setSuRule(project.su_rule);
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
