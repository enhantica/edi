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
    const std::string typed = name.toStdString();
    if (edi::same_space_group_name(typed, group.name_h_m)) {
        return;  // the same group: its code stays as chosen
    }
    const std::optional<edi::SpaceGroupSettingName> setting = edi::space_group_setting_for_name(typed);
    editor_.apply(setting ? edi::Edit::space_group_setting(group, *setting, false) : edi::Edit::assign(group.name_h_m, typed),
                  false);
}

void SpaceGroupViewModel::setCoordSystemCode(const QString& code) {
    edi::SpaceGroup& group = structure_.space_group;
    const std::string chosen = code.toStdString();
    const std::optional<edi::SpaceGroupSettingName> setting = edi::space_group_setting_for_code(it_number_, chosen);
    editor_.apply(setting ? edi::Edit::space_group_setting(group, *setting, false)
                          : edi::Edit::assign(group.coord_system_code, chosen),
                  false);
}

void SpaceGroupViewModel::setItNumber(int number) {
    edi::SpaceGroup& group = structure_.space_group;
    const std::optional<edi::SpaceGroupSettingName> setting =
        number > 0 ? edi::space_group_setting_for_number(number) : std::nullopt;
    editor_.apply(setting ? edi::Edit::space_group_setting(group, *setting, true)
                          : edi::Edit::assign(group.it_number, number > 0 ? std::optional<int>(number) : std::nullopt),
                  false);
}

void SpaceGroupViewModel::sync() {
    const QString name = QString::fromStdString(structure_.space_group.name_h_m);
    // A file declaring the name alone stores no code: the code shown is then the one the name resolves to, the
    // name's only setting; a name with several settings has none until one is chosen. The stored code is unchanged.
    std::string shown_code = structure_.space_group.coord_system_code;
    if (shown_code.empty()) {
        int candidates = 0;
        for (const edi::SpaceGroupSettingName& setting : space_group_settings()) {
            if (edi::same_space_group_name(setting.name_h_m, structure_.space_group.name_h_m)) {
                shown_code = setting.coord_system_code;
                ++candidates;
            }
        }
        if (candidates != 1) {
            shown_code.clear();
        }
    }
    const QString code = QString::fromStdString(shown_code);
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

// ---- AtomSiteAdpListModel -----------------------------------------------------------------------

namespace {
constexpr double kEightPiSq = 8.0 * 3.141592653589793238 * 3.141592653589793238;
}  // namespace

AtomSiteAdpListModel::AtomSiteAdpListModel(edi::Structure& structure, ProjectEditor& editor,
                                           ParameterRegistry& registry,
                                           std::map<const edi::AtomSite*, AdpPreview>& previews, QObject* parent)
    : RowTableModel({"label", "adpType", "active", "adpIso", "iso", "ani11", "ani22", "ani33", "ani12", "ani13",
                     "ani23"},
                    parent),
      structure_(structure),
      editor_(editor),
      registry_(registry),
      previews_(previews) {
    sync();
}

QStringList AtomSiteAdpListModel::types() const {
    return {QStringLiteral("Biso"), QStringLiteral("Uiso"), QStringLiteral("Bani"), QStringLiteral("Uani"),
            QStringLiteral("beta")};
}

AdpCell AtomSiteAdpListModel::cell() const {
    const edi::Cell& c = structure_.cell;
    return {c.length_a.value, c.length_b.value, c.length_c.value,
            c.angle_alpha.value, c.angle_beta.value, c.angle_gamma.value};
}

void AtomSiteAdpListModel::sync() {
    // A removed site's preview goes with it.
    std::erase_if(previews_, [this](const auto& entry) {
        for (const auto& site : structure_.atom_sites) {
            if (site.get() == entry.first) {
                return false;
            }
        }
        return true;
    });
    const AdpCell metric = cell();
    QList<Row> rows;
    for (const auto& site : structure_.atom_sites) {
        const auto found = previews_.find(site.get());
        const bool previewed = found != previews_.end();
        const std::string type = previewed ? found->second.type : std::string("Biso");
        const double b_iso = site->adp_iso.value;
        QList<QVariant> values{QString::fromStdString(site->id), QString::fromStdString(type), !previewed,
                               parameter_role(registry_, &site->adp_iso)};
        if (is_anisotropic(type)) {
            const double b_eq = b_equivalent(found->second.ani, type, metric);
            values.append(type == "Uani" ? b_eq / kEightPiSq : b_eq);
            for (const double component : found->second.ani) {
                values.append(component);
            }
        } else {
            values.append(type == "Uiso" ? b_iso / kEightPiSq : b_iso);
            for (int k = 0; k < 6; ++k) {
                values.append(QVariant());
            }
        }
        rows.append({site.get(), values});
    }
    setTableRows(rows);
    if (has_preview_ != !previews_.empty()) {
        has_preview_ = !previews_.empty();
        emit hasPreviewChanged();
    }
}

void AtomSiteAdpListModel::setType(int row, const QString& type) {
    const auto* site = static_cast<const edi::AtomSite*>(keyAt(row));
    if (site == nullptr || !types().contains(type)) {
        return;
    }
    const std::string to = type.toStdString();
    const auto found = previews_.find(site);
    const std::string from = found != previews_.end() ? found->second.type : std::string("Biso");
    if (to == from) {
        return;
    }
    if (to == "Biso") {
        previews_.erase(site);  // the stored Biso was never changed by a preview
    } else if (!is_anisotropic(to)) {
        previews_[site] = {to, {}};
    } else if (is_anisotropic(from)) {
        previews_[site] = {to, convert_tensor(found->second.ani, from, to, cell())};
    } else {
        previews_[site] = {to, tensor_from_b_iso(to, site->adp_iso.value, cell())};
    }
    sync();
    emit previewsChanged();
}

void AtomSiteAdpListModel::setIso(int row, double value) {
    auto* site = const_cast<edi::AtomSite*>(static_cast<const edi::AtomSite*>(keyAt(row)));
    if (site == nullptr) {
        return;
    }
    const auto found = previews_.find(site);
    const std::string type = found != previews_.end() ? found->second.type : std::string("Biso");
    if (is_anisotropic(type)) {
        return;  // the equivalent value follows the six components
    }
    // A Uiso is the same displacement as the stored B = 8 pi^2 U, which the calculation uses.
    editor_.apply(edi::Edit::value(site->adp_iso, type == "Uiso" ? value * kEightPiSq : value), false);
}

void AtomSiteAdpListModel::setComponent(int row, int component, double value) {
    const auto* site = static_cast<const edi::AtomSite*>(keyAt(row));
    const auto found = previews_.find(site);
    if (site == nullptr || component < 0 || component > 5 || found == previews_.end() ||
        !is_anisotropic(found->second.type)) {
        return;
    }
    found->second.ani[static_cast<std::size_t>(component)] = value;
    sync();
    emit previewsChanged();
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
      atom_site_adps_(new AtomSiteAdpListModel(structure, editor, registry, adp_previews_, this)),
      scattering_lengths_(new ScatteringLengthListModel(structure, editor, this)),
      categories_(new CategoryListModel(this)),
      text_(new BlockText([saved, &structure] { return saved(std::filesystem::path(edi::entity_path("", "structure", structure.name)).generic_string()); }, this)) {
    categories_->setCategories(edi::structure_categories(structure_));
    connect(atom_site_adps_, &AtomSiteAdpListModel::previewsChanged, this, &StructureViewModel::applyAdpPreviews);
    captureScene();
}

void StructureViewModel::captureScene() {
    scene_source_ = edi::capture_scene(structure_);
    applyAdpPreviews();
}

void StructureViewModel::applyAdpPreviews() {
    const edi::Cell& c = structure_.cell;
    const AdpCell cell{c.length_a.value, c.length_b.value, c.length_c.value,
                       c.angle_alpha.value, c.angle_beta.value, c.angle_gamma.value};
    for (edi::SceneSource::SiteAdp& adp : scene_source_.site_adps) {
        adp.u_cartn.reset();
        for (const auto& [site, preview] : adp_previews_) {
            if (site->id.value() == adp.site_id && is_anisotropic(preview.type)) {
                adp.u_cartn = cartesian_u(preview.ani, preview.type, cell, scene_source_.cartn_matrix);
            }
        }
    }
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
    atom_site_adps_->sync();
    scattering_lengths_->sync();
    categories_->setCategories(edi::structure_categories(structure_));
}

}  // namespace edi_app
