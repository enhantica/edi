// SPDX-License-Identifier: BSD-3-Clause
#include "structure_view_model.hpp"

#include <algorithm>
#include <filesystem>

#include "edi/categories.hpp"
#include "edi/edits.hpp"
#include "edi/io.hpp"
#include "parameter_registry.hpp"
#include "project_editor.hpp"

namespace edi_app {

// ---- SpaceGroupViewModel ------------------------------------------------------------------------

SpaceGroupViewModel::SpaceGroupViewModel(edi::Structure& structure, ProjectEditor& editor, QObject* parent)
    : QObject(parent), structure_(structure), editor_(editor) {
    sync();
}

namespace {
// crysta's settings, read once.
const std::vector<edi::SpaceGroupSettingName>& space_group_settings() {
    static const std::vector<edi::SpaceGroupSettingName> settings = edi::space_group_settings();
    return settings;
}
// A name as the pickers compare it: without spaces ("P 1 21/c 1" and "P121/c1" are one name).
std::string unspaced(const std::string& name) {
    std::string out;
    for (const char c : name) {
        if (c != ' ' && c != '\t') {
            out += c;
        }
    }
    return out;
}
// The setting of the lowest ordinal that `pick` accepts: a space group's default setting; null when none.
template <class Pick>
const edi::SpaceGroupSettingName* default_setting(Pick pick) {
    const edi::SpaceGroupSettingName* found = nullptr;
    for (const edi::SpaceGroupSettingName& setting : space_group_settings()) {
        if (pick(setting) && (found == nullptr || setting.setting < found->setting)) {
            found = &setting;
        }
    }
    return found;
}
}  // namespace

QStringList SpaceGroupViewModel::names() const {
    QStringList names;
    for (const edi::SpaceGroupSettingName& setting : space_group_settings()) {
        const QString name = QString::fromStdString(setting.name_h_m);
        if (!names.contains(name)) {
            names.append(name);
        }
    }
    return names;
}

void SpaceGroupViewModel::setNameHM(const QString& name) {
    edi::SpaceGroup& group = structure_.space_group;
    const std::string typed = unspaced(name.toStdString());
    if (typed == unspaced(group.name_h_m)) {
        return;  // the same group: its code stays as chosen
    }
    const edi::SpaceGroupSettingName* setting =
        default_setting([&typed](const edi::SpaceGroupSettingName& s) { return unspaced(s.name_h_m) == typed; });
    editor_.apply(setting != nullptr ? edi::Edit::space_group_setting(group, setting->name_h_m,
                                                                      setting->coord_system_code, setting->it_number,
                                                                      false)
                                     : edi::Edit::assign(group.name_h_m, name.toStdString()),
                  false);
}

void SpaceGroupViewModel::setCoordSystemCode(const QString& code) {
    edi::SpaceGroup& group = structure_.space_group;
    const std::string chosen = code.toStdString();
    const int number = it_number_;
    const edi::SpaceGroupSettingName* setting =
        default_setting([&chosen, number](const edi::SpaceGroupSettingName& s) {
            return s.it_number == number && s.coord_system_code == chosen;
        });
    editor_.apply(setting != nullptr ? edi::Edit::space_group_setting(group, setting->name_h_m,
                                                                      setting->coord_system_code, setting->it_number,
                                                                      false)
                                     : edi::Edit::assign(group.coord_system_code, chosen),
                  false);
}

void SpaceGroupViewModel::setItNumber(int number) {
    edi::SpaceGroup& group = structure_.space_group;
    const edi::SpaceGroupSettingName* setting =
        number > 0 ? default_setting([number](const edi::SpaceGroupSettingName& s) { return s.it_number == number; })
                   : nullptr;
    editor_.apply(setting != nullptr
                      ? edi::Edit::space_group_setting(group, setting->name_h_m, setting->coord_system_code, number,
                                                       true)
                      : edi::Edit::assign(group.it_number, number > 0 ? std::optional<int>(number) : std::nullopt),
                  false);
}

void SpaceGroupViewModel::sync() {
    const QString name = QString::fromStdString(structure_.space_group.name_h_m);
    const QString code = QString::fromStdString(structure_.space_group.coord_system_code);
    // The stored IT number, else the one crysta derives from the setting — the number the Text tab's
    // writer shows (a file declaring the name alone showed an empty number).
    int number = structure_.space_group.it_number.value_or(0);
    QString system;
    try {
        system = QString::fromStdString(edi::crystal_system_name(structure_.space_group));
        number = number > 0 ? number : edi::space_group_it_number(structure_.space_group);
    } catch (const std::exception&) {
        system.clear();  // an unresolvable setting has no crystal system; the calculation says why
    }
    const bool had_number = it_number_ > 0;
    if (name != name_hm_) {
        name_hm_ = name;
        emit nameHMChanged();
    }
    if (code != code_) {
        code_ = code;
        emit coordSystemCodeChanged();
    }
    if (number != it_number_) {
        it_number_ = number;
        std::vector<const edi::SpaceGroupSettingName*> settings;  // the group's, default first
        for (const edi::SpaceGroupSettingName& setting : space_group_settings()) {
            if (setting.it_number == number && !setting.coord_system_code.empty()) {
                settings.push_back(&setting);
            }
        }
        std::stable_sort(settings.begin(), settings.end(),
                         [](const auto* a, const auto* b) { return a->setting < b->setting; });
        QStringList codes;
        for (const edi::SpaceGroupSettingName* setting : settings) {
            codes.append(QString::fromStdString(setting->coord_system_code));
        }
        if (codes != codes_) {
            codes_ = codes;
            emit codesChanged();
        }
        emit itNumberChanged();
        if (had_number != (it_number_ > 0)) {
            emit hasItNumberChanged();
        }
    }
    if (system != crystal_system_) {
        crystal_system_ = system;
        emit crystalSystemChanged();
    }
}

// ---- CellViewModel ------------------------------------------------------------------------------

CellViewModel::CellViewModel(edi::Structure& structure, ParameterRegistry& registry, QObject* parent)
    : QObject(parent), structure_(structure), registry_(registry) {
    sync();
}

void CellViewModel::sync() {
    edi::Cell& cell = structure_.cell;
    edi::Parameter* parameters[6] = {&cell.length_a,    &cell.length_b,   &cell.length_c,
                                     &cell.angle_alpha, &cell.angle_beta, &cell.angle_gamma};
    void (CellViewModel::*const notifiers[6])() = {&CellViewModel::lengthAChanged,    &CellViewModel::lengthBChanged,
                                                  &CellViewModel::lengthCChanged,    &CellViewModel::angleAlphaChanged,
                                                  &CellViewModel::angleBetaChanged, &CellViewModel::angleGammaChanged};
    for (int i = 0; i < 6; ++i) {
        ParameterItem* item = registry_.find(parameters[i]);
        if (item != items_[i]) {
            items_[i] = item;
            emit(this->*notifiers[i])();
        }
    }
}

// ---- AtomSiteListModel --------------------------------------------------------------------------

AtomSiteListModel::AtomSiteListModel(edi::Structure& structure, ProjectEditor& editor, ParameterRegistry& registry,
                                     QObject* parent)
    : RowTableModel({"label", "typeSymbol", "wyckoffLetter", "adpType", "fractX", "fractY", "fractZ", "occupancy",
                     "adpIso"},
                    parent),
      structure_(structure),
      editor_(editor),
      registry_(registry) {
    sync();
}

void AtomSiteListModel::sync() {
    QList<Row> rows;
    for (const auto& site : structure_.atom_sites) {
        rows.append({site.get(),
                     {QString::fromStdString(site->id), QString::fromStdString(site->type_symbol),
                      QString::fromStdString(site->wyckoff_letter), QString::fromStdString(site->adp_type),
                      parameter_role(registry_, &site->fract_x), parameter_role(registry_, &site->fract_y),
                      parameter_role(registry_, &site->fract_z), parameter_role(registry_, &site->occupancy),
                      parameter_role(registry_, &site->adp_iso)}});
    }
    setTableRows(rows);
}

bool AtomSiteListModel::setText(int row, const QString& role, const QString& value) {
    auto* site = const_cast<edi::AtomSite*>(static_cast<const edi::AtomSite*>(keyAt(row)));
    // ADR-0016: the label is the site's id, owned by the structure's atom-site
    // collection (an edi::ItemKey, not a plain string field), so it is handled apart from the
    // three free-text fields.
    const bool label = role == QLatin1String("label");
    // The type symbol and the ADP type record their own writes (edi::detail::WrittenText) and the
    // Wyckoff letter is plain text, so each role has its writer rather than one member pointer.
    const bool text_role = role == QLatin1String("typeSymbol") || role == QLatin1String("wyckoffLetter") ||
                           role == QLatin1String("adpType");
    if (site == nullptr || (!label && !text_role)) {
        return false;
    }
    // A renamed site changes its parameters' paths, so the lists are re-derived; a label another site
    // already carries is refused.
    edi::Structure& structure = structure_;
    const std::string text = value.toStdString();
    const edi::Edit edit = label                                      ? edi::Edit::rename_atom_site(structure, *site, text)
                           : role == QLatin1String("typeSymbol")      ? edi::Edit::assign(site->type_symbol, text)
                           : role == QLatin1String("wyckoffLetter")   ? edi::Edit::assign(site->wyckoff_letter, text)
                                                                      : edi::Edit::assign(site->adp_type, text);
    return editor_.apply(edit, label).isEmpty();
}

void AtomSiteListModel::append() {
    edi::Structure& structure = structure_;
    edi::AtomSite site;
    site.id = unused_name("X", [&structure](const std::string& name) {
        for (const auto& existing : structure.atom_sites) {
            if (existing->id == name) {
                return true;
            }
        }
        return false;
    });
    site.type_symbol = "H";
    editor_.apply(edi::Edit::append(structure.atom_sites, std::move(site)), true);
}

void AtomSiteListModel::duplicate(int row) {
    const auto* source = static_cast<const edi::AtomSite*>(keyAt(row));
    if (source == nullptr) {
        return;
    }
    edi::Structure& structure = structure_;
    edi::AtomSite copy = *source;
    copy.id = unused_name(source->id + "_", [&structure](const std::string& name) {
        for (const auto& existing : structure.atom_sites) {
            if (existing->id == name) {
                return true;
            }
        }
        return false;
    });
    editor_.apply(edi::Edit::append(structure.atom_sites, std::move(copy)), true);
}

void AtomSiteListModel::remove(int row) {
    if (keyAt(row) == nullptr) {
        return;
    }
    edi::Structure& structure = structure_;
    editor_.apply(edi::Edit::erase(structure.atom_sites, static_cast<std::size_t>(row)), true);
}

// ---- ScatteringLengthListModel ------------------------------------------------------------------

ScatteringLengthListModel::ScatteringLengthListModel(edi::Structure& structure, ProjectEditor& editor, QObject* parent)
    : RowTableModel({"typeSymbol", "lengthFm"}, parent), structure_(structure), editor_(editor) {
    sync();
}

void ScatteringLengthListModel::sync() {
    QList<Row> rows;
    for (const auto& [symbol, length] : structure_.scattering_lengths_fm) {
        rows.append({&length, {QString::fromStdString(symbol), length}});
    }
    setTableRows(rows);
}

QString ScatteringLengthListModel::symbolAt(int row) const { return get(row, QStringLiteral("typeSymbol")).toString(); }

bool ScatteringLengthListModel::setTypeSymbol(int row, const QString& symbol) {
    const std::string from = symbolAt(row).toStdString();
    if (from.empty()) {
        return false;
    }
    edi::Structure& structure = structure_;
    // A symbol the structure already declares is refused (the loader's rule), never overwritten.
    return editor_.apply(edi::Edit::rename_scattering_length(structure, from, symbol.toStdString()), false).isEmpty();
}

bool ScatteringLengthListModel::setLengthFm(int row, double length) {
    const std::string symbol = symbolAt(row).toStdString();
    if (symbol.empty()) {
        return false;
    }
    edi::Structure& structure = structure_;
    return editor_.apply(edi::Edit::scattering_length(structure, symbol, length), false).isEmpty();
}

void ScatteringLengthListModel::append() {
    edi::Structure& structure = structure_;
    const std::string symbol = unused_name("X", [&structure](const std::string& name) {
        return structure.scattering_lengths_fm.count(name) != 0;
    });
    editor_.apply(edi::Edit::scattering_length(structure, symbol, 0.0), false);
}

void ScatteringLengthListModel::remove(int row) {
    const std::string symbol = symbolAt(row).toStdString();
    edi::Structure& structure = structure_;
    editor_.apply(edi::Edit::erase_scattering_length(structure, symbol), false);
}

// ---- StructureViewModel -------------------------------------------------------------------------

StructureViewModel::StructureViewModel(SavedFile saved, edi::Structure& structure, ProjectEditor& editor,
                                       ParameterRegistry& registry, QObject* parent)
    : QObject(parent),
      structure_(structure),
      editor_(editor),
      name_(QString::fromStdString(structure.name)),
      space_group_(new SpaceGroupViewModel(structure, editor, this)),
      cell_(new CellViewModel(structure, registry, this)),
      atom_sites_(new AtomSiteListModel(structure, editor, registry, this)),
      scattering_lengths_(new ScatteringLengthListModel(structure, editor, this)),
      categories_(new CategoryListModel(this)),
      text_(new BlockText([saved, &structure] { return saved(std::filesystem::path(edi::entity_path("", "structure", structure.name)).generic_string()); }, this)) {
    categories_->setCategories(edi::structure_categories(structure_));
    captureScene();
}

void StructureViewModel::captureScene() {
    scene_source_ = edi::capture_scene(structure_);
    emit sceneSourceChanged();
}

void StructureViewModel::markSceneStale() {
    if (scene_source_.current) {
        scene_source_.current = false;
        emit sceneWentStale();  // the frame is the same: the view changes its `current` and nothing else
    }
}

void StructureViewModel::setName(const QString& name) {
    edi::Structure& structure = structure_;
    editor_.apply(edi::Edit::structure_name(structure, name.toStdString()), true);
}

void StructureViewModel::sync() {
    const QString name = QString::fromStdString(structure_.name);
    if (name != name_) {
        name_ = name;
        emit nameChanged();
    }
    space_group_->sync();
    cell_->sync();
    atom_sites_->sync();
    scattering_lengths_->sync();
    categories_->setCategories(edi::structure_categories(structure_));
}

}  // namespace edi_app
