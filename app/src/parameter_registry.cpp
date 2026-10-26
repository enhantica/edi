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
    refreshSpelling(project);
    refreshDefiniteness(project);
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
    for (const auto& structure : project.structures) {
        for (const auto& site : structure->atom_sites) {
            for (const edi::Parameter* parameter :
                 {&site->fract_x, &site->fract_y, &site->fract_z, &site->occupancy, &site->adp_iso}) {
                element.emplace(parameter, site->type_symbol);
            }
            for (const auto& tensor : structure->atom_site_aniso) {
                if (tensor->id.value() == site->id.value()) {
                    for (const edi::Parameter* parameter : tensor->parameters()) {
                        element.emplace(parameter, site->type_symbol);
                    }
                }
            }
        }
    }
    // An ADP's label and units for its site's declared type, from the dictionary's variants.
    const std::unordered_map<const edi::Parameter*, std::string> variants = edi::parameter_variants(project);
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
        if (const auto variant = variants.find(item->parameter()); variant != variants.end()) {
            const std::string uid = item->uid().toStdString();
            item->setLabel(QString::fromStdString(edi::label(uid, variant->second)),
                           QString::fromStdString(edi::units_label(uid, variant->second)));
            item->setVariant(QString::fromStdString(variant->second));
        } else if (!item->variant().isEmpty()) {
            // A variant the parameter no longer has (a doublet switched off) gives back the item's own label.
            const std::string uid = item->uid().toStdString();
            item->setLabel(QString::fromStdString(edi::label(uid)), QString::fromStdString(edi::units_label(uid)));
            item->setVariant(QString());
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

void ParameterRegistry::refreshSpelling(const edi::Project& project) {
    // A field shows a value as the save writes it, exactly where the save does: a cell that rounded would not
    // load, or every value. That follows any edit, so it is read again with the rule at every publish.
    const edi::SaveSpelling spelling = edi::save_spelling(project);
    for (ParameterItem* item : items_) {
        item->setSpelling(project.su_rule, edi::written_exactly(spelling, project, *item->parameter()));
    }
}

void ParameterRegistry::refreshDefiniteness(const edi::Project& project) {
    // A tensor with a negative eigenvalue is kept and shown red, each of its components naming why (the owner,
    // 2026-10-23).
    std::unordered_map<const edi::Parameter*, QString> warned;
    for (const edi::AdpDefinitenessWarning& warning : edi::adp_definiteness_warnings(project)) {
        const edi::AtomSiteAniso& tensor = *warning.tensor;
        for (const edi::Parameter* component : {&tensor.adp_11, &tensor.adp_22, &tensor.adp_33, &tensor.adp_12,
                                                &tensor.adp_13, &tensor.adp_23}) {
            warned[component] = QString::fromStdString(warning.message);
        }
    }
    for (ParameterItem* item : items_) {
        const auto found = warned.find(item->parameter());
        item->setDomainWarning(found != warned.end() ? found->second : QString());
    }
}

void ParameterRegistry::publish(edi::Project& project) {
    refreshElements(project);
    refreshRefinable(project);
    refreshEstimated(project);
    refreshSpelling(project);
    refreshDefiniteness(project);
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
