// SPDX-License-Identifier: BSD-3-Clause
#include "structure_view_model.hpp"

#include <QRegularExpression>
#include <QSet>
#include <algorithm>
#include <set>
#include <array>
#include <cmath>
#include <limits>
#include <filesystem>
#include <map>
#include <optional>
#include <string>

#include "crysta/magnetic.hpp"
#include "edi/categories.hpp"
#include "edi/edits.hpp"
#include "edi/io.hpp"
#include "edi/selectors.hpp"
#include "edi/symmetry.hpp"
#include "parameter_item.hpp"
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
// The categories as the Structure page shows them: the Atomic displacement group lists one row per atom site, of
// any ADP type, so its count is the sites', not the anisotropic tensors' the core loop holds (the owner, 2026-11-04).
std::vector<edi::Category> shown_categories(edi::Structure& structure) {
    std::vector<edi::Category> categories = edi::structure_categories(structure);
    // Crystal or Magnetic (edi ADR-0078): a Crystal structure shows no magnetic group, the moments included; a Magnetic
    // one shows its Magnetic space group in place of Space group, its derived symbols and parent group on Extra.
    static const std::set<std::string> magnetic_ids{"space_group_magn", "parent_space_group", "parent_propagation_vector",
                                                    "space_group_symop_magn_operation", "space_group_symop_magn_centering",
                                                    "atom_site_moment", "magnetic_form_factor"};
    const bool magnetic = edi::structure_magnetic(structure);
    std::erase_if(categories, [magnetic](const edi::Category& category) {
        return magnetic ? category.id == "space_group" : magnetic_ids.contains(category.id);
    });
    if (magnetic) {
        const auto has = [&categories](const char* id) {
            return std::any_of(categories.begin(), categories.end(), [id](const edi::Category& category) { return category.id == id; });
        };
        // A grey group gives no moment yet, so the core lists only the moments: the groups a Magnetic structure always has.
        if (!has("space_group_magn")) categories.push_back({"space_group_magn"});
        if (!has("parent_space_group")) categories.push_back({"parent_space_group"});
        if (!has("parent_propagation_vector"))
            categories.push_back({"parent_propagation_vector", true, structure.magnetic->propagation_vectors.size()});
        if (!has("space_group_symop_magn_operation"))
            categories.push_back({"space_group_symop_magn_operation", true, structure.magnetic->operations.size()});
        categories.push_back({"space_group_magn_symbols"});
    }
    // The bond cutoffs and the bonds they give: a designed group in Extra (GeomGroup.qml).
    edi::Category geom;
    geom.id = "geom";
    categories.push_back(std::move(geom));
    for (edi::Category& category : categories)
        if (category.id == "atom_site_aniso") category.rows = structure.atom_sites.size();
    // A Le Bail or Pawley structure shows no atom sites, displacements or moments; they stay in the model (edi ADR-0109).
    std::erase_if(categories, [&structure](const edi::Category& category) {
        return edi::structure_page_hides(structure, category.id);
    });
    return categories;
}

// The categories the page leaves out though the structure's text carries them, so no group is made for them.
std::vector<std::string> hidden_categories(const edi::Structure& structure) {
    std::vector<std::string> hidden;
    for (const char* id : {"atom_site", "atom_site_aniso", "atom_site_moment"}) {
        if (edi::structure_page_hides(structure, id)) hidden.emplace_back(id);
    }
    return hidden;
}
}  // namespace

QStringList SpaceGroupViewModel::names() const {
    // The settings table never changes, so its names are collected once: the name box reads them on every
    // change of the group, and collecting them took about a tenth of a second.
    static const QStringList all = [] {
        QStringList names;
        QSet<QString> seen;
        for (const edi::SpaceGroupSettingName& setting : space_group_settings()) {
            const QString name = QString::fromStdString(setting.name_h_m);
            if (!seen.contains(name)) {
                seen.insert(name);
                names.append(name);
            }
        }
        return names;
    }();
    return all;
}

namespace {
// After an applied setting change: an explicit setting is a declared one, and a magnetic
// structure takes its accepted state as crysta completes it (edi ADR-0078).
void commit_setting(edi::Structure& structure) {
    if (structure.magnetic->operations.empty()) {
        return;
    }
    if (!structure.magnetic->space_group_declared) {
        structure.magnetic.modify([](edi::MagneticDescription& magnetic) { magnetic.space_group_declared = true; });
    }
    edi::complete_atom_site_moments(structure);
}

// Whether crysta's acceptance rule refuses a magnetic structure's setting change (edi ADR-0078),
// tried on a copy; the change is then not applied and the prior model stays.
template <typename Change>
bool setting_refused(const edi::Structure& structure, Change change) {
    if (structure.magnetic->operations.empty()) {
        return false;
    }
    edi::Structure trial = structure;
    change(trial.space_group);
    trial.magnetic.modify([](edi::MagneticDescription& magnetic) { magnetic.space_group_declared = true; });
    try {
        edi::check_magnetic_acceptance(trial);
    } catch (const std::exception&) {
        return true;
    }
    return false;
}
}  // namespace

void SpaceGroupViewModel::setNameHM(const QString& name) {
    edi::SpaceGroup& group = structure_.space_group;
    const std::string typed = name.toStdString();
    if (edi::same_space_group_name(typed, group.name_h_m)) {
        return;  // the same group: its code stays as chosen
    }
    const std::optional<edi::SpaceGroupSettingName> setting = edi::space_group_setting_for_name(typed);
    if (setting_refused(structure_, [&](edi::SpaceGroup& trial) {
            setting ? edi::assign_space_group_setting(trial, *setting, false) : void(trial.name_h_m = typed);
        })) {
        return;
    }
    editor_.apply_creation_control(setting ? edi::Edit::space_group_setting(group, *setting, false) : edi::Edit::assign(group.name_h_m, typed),
                  false,{ProjectEditor::CreationAction::Kind::SpaceGroupName,&structure_,{},name});
    commit_setting(structure_);
}

void SpaceGroupViewModel::setCoordSystemCode(const QString& code) {
    edi::SpaceGroup& group = structure_.space_group;
    const std::string chosen = code.toStdString();
    const std::optional<edi::SpaceGroupSettingName> setting = edi::space_group_setting_for_code(it_number_, chosen);
    if (setting_refused(structure_, [&](edi::SpaceGroup& trial) {
            setting ? edi::assign_space_group_setting(trial, *setting, false) : void(trial.coord_system_code = chosen);
        })) {
        return;
    }
    editor_.apply_creation_control(setting ? edi::Edit::space_group_setting(group, *setting, false)
                          : edi::Edit::assign(group.coord_system_code, chosen),
                  false,{ProjectEditor::CreationAction::Kind::SpaceGroupSetting,&structure_,{},code});
    commit_setting(structure_);
}

void SpaceGroupViewModel::setItNumber(int number) {
    if (number > 230) {
        return;  // no such space-group type: never stored
    }
    edi::SpaceGroup& group = structure_.space_group;
    const std::optional<edi::SpaceGroupSettingName> setting =
        number > 0 ? edi::space_group_setting_for_number(number) : std::nullopt;
    if (setting && setting_refused(structure_, [&](edi::SpaceGroup& trial) {
            edi::assign_space_group_setting(trial, *setting, true);
        })) {
        return;
    }
    editor_.apply_creation_control(setting ? edi::Edit::space_group_setting(group, *setting, true)
                          : edi::Edit::assign(group.it_number, number > 0 ? std::optional<int>(number) : std::nullopt),
                  false,{ProjectEditor::CreationAction::Kind::SpaceGroupNumber,&structure_,{},{},static_cast<double>(number)});
    commit_setting(structure_);
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

namespace {

// A Wyckoff representative as crysta's table spells it ("1/2*x+1/2*y,1/2*x+1/2*y,z") as the WP list shows it
// ("½x+½y, ½x+½y, z"): the common fractions as one glyph, no multiplication sign, a minus sign and a space after
// each comma. Display only.
QString wyckoff_coordinates_display(const std::string& representative) {
    static const std::map<QString, QString> glyphs{
        {QStringLiteral("1/2"), QStringLiteral("\u00BD")}, {QStringLiteral("1/3"), QStringLiteral("\u2153")},
        {QStringLiteral("2/3"), QStringLiteral("\u2154")}, {QStringLiteral("1/4"), QStringLiteral("\u00BC")},
        {QStringLiteral("3/4"), QStringLiteral("\u00BE")}, {QStringLiteral("1/6"), QStringLiteral("\u2159")},
        {QStringLiteral("5/6"), QStringLiteral("\u215A")}, {QStringLiteral("1/8"), QStringLiteral("\u215B")},
        {QStringLiteral("3/8"), QStringLiteral("\u215C")}, {QStringLiteral("5/8"), QStringLiteral("\u215D")},
        {QStringLiteral("7/8"), QStringLiteral("\u215E")}};
    QString text = QString::fromStdString(representative);
    static const QRegularExpression fraction(QStringLiteral("(\\d+)/(\\d+)"));
    QString out;
    qsizetype last = 0;
    for (QRegularExpressionMatchIterator match = fraction.globalMatch(text); match.hasNext();) {
        const QRegularExpressionMatch found = match.next();
        out += text.mid(last, found.capturedStart() - last);
        const auto glyph = glyphs.find(found.captured(0));
        out += glyph != glyphs.end() ? glyph->second : found.captured(0);
        last = found.capturedEnd();
    }
    out += text.mid(last);
    out.remove(QLatin1Char('*'));
    out.replace(QLatin1Char('-'), QChar(0x2212));
    out.replace(QLatin1Char(','), QStringLiteral(", "));
    return out;
}

}  // namespace

void AtomSiteListModel::sync() {
    QList<Row> rows;
    const bool lettered = edi::takes_wyckoff_letter(structure_);
    for (const auto& site : structure_.atom_sites) {
        rows.append({site.get(),
                     {QString::fromStdString(site->id), QString::fromStdString(site->type_symbol),
                      lettered ? QString::fromStdString(site->wyckoff_letter) : QString(),
                      QString::fromStdString(site->adp_type),
                      parameter_role(registry_, &site->fract_x), parameter_role(registry_, &site->fract_y),
                      parameter_role(registry_, &site->fract_z), parameter_role(registry_, &site->occupancy),
                      parameter_role(registry_, &site->adp_iso)}});
    }
    setTableRows(rows);
    QStringList letters;
    QStringList names;
    QStringList labels;
    for (const edi::WyckoffOption& option : edi::wyckoff_positions(structure_)) {
        const QString name = QStringLiteral("%1%2").arg(option.multiplicity).arg(QString::fromStdString(option.letter));
        letters.append(QString::fromStdString(option.letter));
        names.append(name);
        labels.append(name + QStringLiteral(": ") + wyckoff_coordinates_display(option.coordinates));
    }
    if (letters != wyckoff_letters_) {
        wyckoff_letters_ = letters;
        emit wyckoffLettersChanged();
    }
    if (names != wyckoff_names_) {
        wyckoff_names_ = names;
        emit wyckoffNamesChanged();
    }
    if (labels != wyckoff_labels_) {
        wyckoff_labels_ = labels;
        emit wyckoffLabelsChanged();
    }
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
                           : role == QLatin1String("typeSymbol")      ? edi::Edit::site_type(structure, *site, text)
                           : role == QLatin1String("wyckoffLetter")   ? edi::Edit::assign(site->wyckoff_letter, text)
                                                                      : edi::Edit::adp_type(structure, *site, text);
    // A type change can add or remove a tensor row, which changes the parameter set.
    // A new element can drop a moment its ions cannot carry, which changes the parameter set too.
    return editor_.apply_creation_control(edit, label || role == QLatin1String("adpType") || role == QLatin1String("typeSymbol"),
        {ProjectEditor::CreationAction::Kind::AtomText,site,role,value}).isEmpty();
}

std::optional<std::uint64_t>& AtomSiteListModel::fixedSeed() {
    static std::optional<std::uint64_t> seed;
    return seed;
}

void AtomSiteListModel::fixRandomSeed(std::uint64_t seed) { fixedSeed() = seed; }

void AtomSiteListModel::append() {
    edi::Structure& structure = structure_;
    // A random element on the general position at random coordinates (the owner, 2026-10-11, edi::new_atom_site).
    if (!random_.has_value()) {
        random_.emplace(fixedSeed().value_or(std::random_device{}()));
    }
    std::uniform_real_distribution<double> unit(0.0, 1.0);
    edi::AtomSite site = edi::new_atom_site(structure, [this, &unit] { return unit(*random_); });
    const ProjectEditor::CreationAction action{ProjectEditor::CreationAction::Kind::AtomAppend,&structure,{},QString::fromStdString(site.id.value())};
    editor_.apply_creation_control(edi::Edit::append(structure.atom_sites, site), true, action);
}

void AtomSiteListModel::duplicate(int row) {
    const auto* source = static_cast<const edi::AtomSite*>(keyAt(row));
    if (source == nullptr) {
        return;
    }
    edi::Structure& structure = structure_;
    const std::string id = unused_name(source->id + "_", [&structure](const std::string& name) {
        for (const auto& existing : structure.atom_sites) {
            if (existing->id == name) {
                return true;
            }
        }
        return false;
    });
    editor_.apply(edi::Edit::duplicate_atom_site(structure, *source, id), true);
}

void AtomSiteListModel::remove(int row) {
    if (keyAt(row) == nullptr) {
        return;
    }
    edi::Structure& structure = structure_;
    editor_.apply_creation_control(edi::Edit::erase_atom_site(structure, static_cast<std::size_t>(row)), true,
        {ProjectEditor::CreationAction::Kind::AtomRemove, keyAt(row), {}, {}, 0});
}

// ---- AtomSiteAdpListModel -----------------------------------------------------------------------

AtomSiteAdpListModel::AtomSiteAdpListModel(edi::Structure& structure, ProjectEditor& editor,
                                           ParameterRegistry& registry, QObject* parent)
    : RowTableModel({"label", "adpType", "adpIso", "ani11", "ani22", "ani33", "ani12", "ani13", "ani23"}, parent),
      structure_(structure),
      editor_(editor),
      registry_(registry) {
    sync();
}

QStringList AtomSiteAdpListModel::types() const {
    return {QStringLiteral("Biso"), QStringLiteral("Uiso"), QStringLiteral("Bani"), QStringLiteral("Uani"),
            QStringLiteral("beta")};
}

void AtomSiteAdpListModel::sync() {
    QList<Row> rows;
    bool anisotropic = false;
    for (const auto& site : structure_.atom_sites) {
        const std::string type = site->adp_type.value();
        anisotropic = anisotropic || type == "Bani" || type == "Uani" || type == "beta";
        QList<QVariant> values{QString::fromStdString(site->id), QString::fromStdString(site->adp_type),
                               parameter_role(registry_, &site->adp_iso)};
        const edi::AtomSiteAniso* tensor = nullptr;
        for (const auto& row : structure_.atom_site_aniso) {
            if (row->id.value() == site->id.value()) {
                tensor = row.get();
            }
        }
        for (const edi::Parameter* component :
             tensor != nullptr ? const_cast<edi::AtomSiteAniso*>(tensor)->parameters() : std::vector<edi::Parameter*>{}) {
            values.append(parameter_role(registry_, component));
        }
        while (values.size() < 9) {
            values.append(QVariant());
        }
        rows.append({site.get(), values});
    }
    setTableRows(rows);
    if (anisotropic != anisotropic_) {
        anisotropic_ = anisotropic;
        emit anisotropicChanged();
    }
}

void AtomSiteAdpListModel::setType(int row, const QString& type) {
    auto* site = const_cast<edi::AtomSite*>(static_cast<const edi::AtomSite*>(keyAt(row)));
    if (site == nullptr || !types().contains(type) || site->adp_type.value() == type.toStdString()) {
        return;
    }
    // A tensor row comes or goes: the parameter set changes.
    editor_.apply_creation_control(edi::Edit::adp_type(structure_, *site, type.toStdString()), true,
        {ProjectEditor::CreationAction::Kind::AtomAdpType,site,{},type});
}

// ---- AtomSiteMomentListModel --------------------------------------------------------------------

namespace {
// A refusal in plain words for the page (the owner, 2026-11-19): crysta's text names the item it refused
// (`_category.item 'value' ...`), which the page does not show; the known propagation-vector reasons are said as
// what the user can do.
QString plain_refusal(const QString& raw) {
    QString text = raw;
    static const QRegularExpression tag(QStringLiteral(R"(^_[A-Za-z0-9_]+\.[A-Za-z0-9_.-]+\s+'[^']*'\s*:?\s*)"));
    text.remove(tag);
    static const QRegularExpression vector(QStringLiteral(R"(^propagation vector '[^']*' \(([^)]*)\):\s*(.*)$)"));
    const QRegularExpressionMatch found = vector.match(text);
    if (!found.hasMatch()) {
        return text.isEmpty() ? text : text.left(1).toUpper() + text.mid(1);
    }
    const QString k = found.captured(1);
    const QString reason = found.captured(2);
    static const QRegularExpression axis(QStringLiteral(R"(cell's ([abc])' axis is not a period)"));
    if (const QRegularExpressionMatch along = axis.match(reason); along.hasMatch()) {
        const QString letter = along.captured(1);
        const QStringList parts = k.split(QLatin1Char(','));
        const int index = letter.at(0).unicode() - 'a';
        int times = 0;
        if (index >= 0 && index < parts.size()) {
            const QStringList fraction = parts.at(index).trimmed().split(QLatin1Char('/'));
            if (fraction.size() == 2) times = fraction.at(1).toInt();
        }
        const QString longer = times == 2 ? QObject::tr("twice as long") : times > 2 ? QObject::tr("%1 times as long").arg(times)
                                                                                    : QObject::tr("longer");
        return QObject::tr("k = %1 needs a cell %2 along %3, which this magnetic group's cell cannot carry. Choose a "
                           "group with that cell, or a k this cell carries.").arg(k, longer, letter);
    }
    if (reason.contains(QLatin1String("grey group admits only k = 0"))) {
        return QObject::tr("A grey group (every moment zero) carries only k = 0,0,0. Choose a magnetic subgroup first.");
    }
    static const QRegularExpression translation(QStringLiteral(R"(the translation \(([^)]*)\) does not keep it)"));
    if (const QRegularExpressionMatch kept = translation.match(reason); kept.hasMatch()) {
        return QObject::tr("k = %1 does not agree with the group's translation %2, so this group cannot carry it.")
            .arg(k, kept.captured(1));
    }
    return QObject::tr("k = %1 was not taken: %2").arg(k, reason);
}
}  // namespace

AtomSiteMomentListModel::AtomSiteMomentListModel(edi::Structure& structure, ProjectEditor& editor,
                                                 ParameterRegistry& registry, QObject* parent)
    : RowTableModel({"label", "ion", "mx", "my", "mz", "symmform", "type"}, parent),
      structure_(structure),
      editor_(editor),
      registry_(registry) {
    sync();
}

void AtomSiteMomentListModel::sync() {
    QList<Row> rows;
    for (const auto& site : structure_.atom_sites) {
        const edi::AtomSiteMoment* moment = nullptr;
        for (const auto& row : structure_.atom_site_moment) {
            if (row->id.value() == site->id.value()) {
                moment = row.get();
            }
        }
        QString ion = QStringLiteral("none");
        if (moment != nullptr) {
            std::string declared;
            for (const auto& row : structure_.magnetic_form_factors) {
                if (row->id.value() == site->type_symbol.value()) {
                    declared = row->ion.value();
                }
            }
            ion = !declared.empty() ? QString::fromStdString(declared)
                                    : QString::fromStdString(crysta::magnetic_type_ion(site->type_symbol.value()));
        }
        QList<QVariant> values{QString::fromStdString(site->id), ion};
        if (moment != nullptr) {
            for (const edi::Parameter* component : const_cast<edi::AtomSiteMoment*>(moment)->parameters()) {
                values.append(parameter_role(registry_, component));
            }
            values.append(QString::fromStdString(moment->symmform));
        } else {
            values << QVariant() << QVariant() << QVariant() << QString();
        }
        // The site's element: the ion choices follow it (the owner, 2026-11-19).
        values.append(QString::fromStdString(site->type_symbol.value()));
        rows.append({site.get(), values});
    }
    setTableRows(rows);
    ++revision_;
    emit revisionChanged();
}

QStringList AtomSiteMomentListModel::ions(int row, const QString& /*type*/) const {
    const auto* site = static_cast<const edi::AtomSite*>(keyAt(row));
    QStringList out{QStringLiteral("none")};
    if (site != nullptr) {
        for (const std::string& ion : crysta::magnetic_ions_for_type(site->type_symbol.value())) {
            out.append(QString::fromStdString(ion));
        }
    }
    return out;
}

void AtomSiteMomentListModel::setIon(int row, const QString& ion) {
    const auto* site = static_cast<const edi::AtomSite*>(keyAt(row));
    if (site == nullptr) {
        return;
    }
    edi::Structure& structure = structure_;
    const bool magnetic = !ion.isEmpty() && ion != QLatin1String("none");
    // The moment row comes or goes: the parameter set changes.
    editor_.apply(edi::Edit::moment_site(structure, *site, magnetic), true);
    if (magnetic) {
        // The type's form-factor row may come or go with its ion: the parameter set changes.
        editor_.apply(edi::Edit::magnetic_ion(structure, site->type_symbol.value(), ion.toStdString()), true);
    }
}

MagneticFormFactorListModel::MagneticFormFactorListModel(edi::Structure& structure, ProjectEditor& editor,
                                                         ParameterRegistry& registry, QObject* parent)
    : RowTableModel({"type", "ion", "approximation", "c2", "c4", "c6"}, parent),
      structure_(structure),
      editor_(editor),
      registry_(registry) {
    sync();
}

namespace {
// The structure's form-factor row of an atom type, or null.
const edi::MagneticFormFactor* form_factor_of(const edi::Structure& structure, const std::string& type_symbol) {
    for (const auto& row : structure.magnetic_form_factors) {
        if (row->id.value() == type_symbol) {
            return row.get();
        }
    }
    return nullptr;
}

// The terms an atom type's given coefficients carry whole (<j0>, <j2>, <j4>, <j6>), or nothing when its file gives
// none or no whole <j0>, which leaves it on its ion's table (crysta's rule, ADR-0108 §5).
std::optional<std::array<bool, 4>> given_terms(const edi::Structure& structure, const std::string& type_symbol) {
    for (const auto& [symbol, given] : structure.magnetic->radial_coefficients) {
        if (symbol != type_symbol) continue;
        std::array<bool, 4> whole{};
        for (std::size_t term = 0; term < 4; ++term) {
            whole[term] = std::all_of(given.values.begin() + static_cast<std::ptrdiff_t>(8 * term),
                                      given.values.begin() + static_cast<std::ptrdiff_t>(8 * term + 7),
                                      [](const std::string& value) { return !value.empty(); });
        }
        if (whole[0]) return whole;
        break;
    }
    return std::nullopt;
}
}  // namespace

void MagneticFormFactorListModel::sync() {
    QList<Row> rows;
    std::set<std::string> seen;
    for (const auto& site : structure_.atom_sites) {
        const std::string type = site->type_symbol.value();
        const bool magnetic = std::any_of(structure_.atom_site_moment.begin(), structure_.atom_site_moment.end(),
                                          [&site](const auto& moment) { return moment->id.value() == site->id.value(); });
        if (!magnetic || !seen.insert(type).second) {
            continue;
        }
        const edi::MagneticFormFactor* declared = form_factor_of(structure_, type);
        // A type whose file gives its coefficients shows them as its source, read only: they replace the ion's table.
        const std::string ion = given_terms(structure_, type) ? QObject::tr("given").toStdString()
                                : declared != nullptr && !declared->ion.value().empty() ? declared->ion.value()
                                                                                        : crysta::magnetic_type_ion(type);
        QList<QVariant> values{QString::fromStdString(type), QString::fromStdString(ion),
                               QString::fromStdString(declared != nullptr ? declared->approximation.value() : "j0")};
        if (declared != nullptr) {
            for (const edi::Parameter* coefficient : const_cast<edi::MagneticFormFactor*>(declared)->parameters()) {
                values.append(parameter_role(registry_, coefficient));
            }
        } else {
            values << QVariant() << QVariant() << QVariant();
        }
        rows.append({site.get(), values});
    }
    setTableRows(rows);
}

QStringList MagneticFormFactorListModel::approximations() const {
    return {QStringLiteral("j0"), QStringLiteral("dipole"), QStringLiteral("beyond_dipole")};
}

bool MagneticFormFactorListModel::hasTerm(int row, int n) const {
    const std::string ion = text(row, QStringLiteral("ion")).toStdString();
    if (ion.empty() || n < 0 || n > 2) {
        return false;
    }
    if (const std::optional<std::array<bool, 4>> given = given_terms(structure_, text(row, QStringLiteral("type")).toStdString())) {
        return (*given)[static_cast<std::size_t>(n) + 1];
    }
    try {
        return crysta::magnetic_ion_table(ion).has[static_cast<std::size_t>(n)];
    } catch (const std::exception&) {
        return false;
    }
}

void MagneticFormFactorListModel::setApproximation(int row, const QString& approximation) {
    const auto* site = static_cast<const edi::AtomSite*>(keyAt(row));
    if (site == nullptr || approximation == text(row, QStringLiteral("approximation"))) {
        return;
    }
    // A form-factor row may come or go: the parameter set changes.
    editor_.apply(edi::Edit::magnetic_approximation(structure_, site->type_symbol.value(), approximation.toStdString()),
                  true);
}

namespace {
std::array<double, 6> cell_of(const edi::Structure& structure) {
    const edi::Cell& cell = structure.cell;
    return {cell.length_a.value, cell.length_b.value, cell.length_c.value,
            cell.angle_alpha.value, cell.angle_beta.value, cell.angle_gamma.value};
}

const edi::AtomSiteMoment* moment_of(const edi::Structure& structure, const edi::AtomSite* site) {
    if (site == nullptr) {
        return nullptr;
    }
    for (const auto& row : structure.atom_site_moment) {
        if (row->id.value() == site->id.value()) {
            return row.get();
        }
    }
    return nullptr;
}

// The covariance of a moment's crystal-axis components and its structure's cell that every form's
// s.u. comes from: crysta's mapping of the fit's seeds through the project's relation graph
// (edi::moment_input_covariance; crysta's rule for an undefined s.u., edi ADR-0078). Nothing is
// rebuilt here. A structure no project holds has no seeds, so its forms show no s.u.
// Relations that cannot hold (an alias naming an atom the structure no longer has) leave every s.u. undefined: the
// table is read from a binding, where a refusal would end the app; the edit that broke them says why.
std::array<double, 81> moment_covariance(const edi::Project* project, const edi::Structure& structure,
                                         const edi::AtomSiteMoment& moment) {
    if (project != nullptr) {
        for (std::size_t index = 0; index < project->structures.size(); ++index) {
            if (project->structures[index].get() == &structure) {
                try {
                    return edi::moment_input_covariance(*project, index, moment.id.value());
                } catch (const std::exception&) {
                    std::array<double, 81> undefined{};
                    undefined.fill(std::numeric_limits<double>::quiet_NaN());
                    return undefined;
                }
            }
        }
    }
    return {};
}

std::array<double, 3> in_form(const std::array<double, 6>& cell, const std::array<double, 3>& crystal,
                              const QString& form) {
    if (form == QLatin1String("cartesian")) {
        return crysta::moment_cartesian(cell, crystal);
    }
    if (form == QLatin1String("spherical")) {
        return crysta::moment_spherical(crysta::moment_cartesian(cell, crystal));
    }
    return crystal;
}
}  // namespace

QList<double> AtomSiteMomentListModel::components(int row, const QString& form) const {
    const auto* site = static_cast<const edi::AtomSite*>(keyAt(row));
    const edi::AtomSiteMoment* moment = moment_of(structure_, site);
    if (moment == nullptr) {
        return {};
    }
    const std::array<double, 6> cell = cell_of(structure_);
    const std::array<double, 3> crystal{moment->crystalaxis_x.value, moment->crystalaxis_y.value,
                                        moment->crystalaxis_z.value};
    const edi::Project* project = editor_.currentProject();
    const bool fitted = project != nullptr && project->fit_result.held();
    // Every form's s.u. comes from crysta's one function on the components' and the cell's
    // covariance; an undefined input makes the values that depend on it undefined (NaN), never 0.
    const std::array<double, 81> covariance = moment_covariance(project, structure_, *moment);
    bool has_su = fitted;
    for (std::size_t i = 0; i < 81 && !has_su; i += 10) {
        has_su = covariance[i] != 0.0;  // a diagonal entry: some input has an s.u. (or none known)
    }
    const std::array<double, 3> values = in_form(cell, crystal, form);
    const std::array<double, 3> spherical = crysta::moment_spherical(crysta::moment_cartesian(cell, crystal));
    const std::array<double, 4> derived = crysta::moment_form_su(cell, crystal, form.toStdString(), covariance);
    const std::array<double, 3> values_su{derived[0], derived[1], derived[2]};
    const std::array<double, 3> spherical_su{derived[3], 0.0, 0.0};
    // The spherical values a moment does not determine: all three at a zero moment, the azimuth with no component
    // across z. They show no s.u.
    const std::array<double, 3> cartesian = crysta::moment_cartesian(cell, crystal);
    const double across = std::hypot(cartesian[0], cartesian[1]);
    const bool zero = std::hypot(across, cartesian[2]) < 1e-12;
    int undetermined = 0;
    if (form == QLatin1String("spherical")) {
        undetermined = zero ? 0b110 : across < 1e-12 ? 0b100 : 0;
    }
    const double nan = std::numeric_limits<double>::quiet_NaN();
    QList<double> out;
    for (const double value : values) {
        out.append(value);
    }
    for (std::size_t k = 0; k < 3; ++k) {
        out.append(has_su && (undetermined & (1 << k)) == 0 ? values_su[k] : nan);
    }
    out.append(spherical[0]);
    // A fitted zero moment keeps the bound on |M| in every form; without a fit's covariance it is NaN there.
    out.append(has_su ? spherical_su[0] : nan);
    // How the s.u. were found, and which values the moment does not determine (bit k: value k).
    out.append(fitted && has_su ? 1.0 : 0.0);
    out.append(undetermined);
    return out;
}

QString AtomSiteMomentListModel::setComponent(int row, const QString& form, int k, double value) {
    const auto* site = static_cast<const edi::AtomSite*>(keyAt(row));
    const edi::AtomSiteMoment* moment = moment_of(structure_, site);
    QString refusal;
    if (moment == nullptr || k < 0 || k > 2) {
        refusal = tr("This site has no moment to edit");
    } else {
        // The core decides what the symmetry and the project's constraints admit, and which components to write.
        const edi::Project* project = editor_.currentProject();
        if (project == nullptr) {
            refusal = tr("This site has no moment to edit");
        } else {
            const edi::MomentEdit edit = edi::moment_edit(*project, structure_, *moment, form.toStdString(),
                                                          static_cast<std::size_t>(k), value);
            refusal = QString::fromStdString(edit.refusal);
            if (refusal.isEmpty()) {
                const std::vector<edi::Parameter*> components =
                    const_cast<edi::AtomSiteMoment*>(moment)->parameters();
                std::vector<std::pair<edi::Parameter*, double>> writes;
                writes.reserve(edit.writes.size());
                for (const auto& [i, written] : edit.writes) {
                    writes.emplace_back(components[i], written);
                }
                refusal = editor_.apply(edi::Edit::values(std::move(writes)), false);
            }
        }
    }
    refusal = plain_refusal(refusal);
    if (refusal != refusal_) {
        refusal_ = refusal;
        emit refusalChanged();
    }
    return refusal;
}

// ---- PropagationVectorListModel -----------------------------------------------------------------

PropagationVectorListModel::PropagationVectorListModel(edi::Structure& structure, ProjectEditor& editor, QObject* parent)
    : RowTableModel({"id", "vector"}, parent), structure_(structure), editor_(editor) {
    sync();
}

void PropagationVectorListModel::sync() {
    const auto& vectors = structure_.magnetic->propagation_vectors;
    QList<Row> rows;
    for (std::size_t i = 0; i < vectors.size(); ++i) {
        rows.append({&vectors[i], {QString::fromStdString(vectors[i].first), QString::fromStdString(vectors[i].second)}});
    }
    setTableRows(rows);
}

bool PropagationVectorListModel::replace(std::vector<std::pair<std::string, std::string>> rows) {
    edi::Structure& structure = structure_;
    const QString refusal = plain_refusal(editor_.apply(edi::Edit::propagation_vectors(structure, std::move(rows)), true));
    if (refusal != refusal_) {
        refusal_ = refusal;
        emit refusalChanged();
    }
    return refusal.isEmpty();
}

bool PropagationVectorListModel::setId(int row, const QString& id) {
    auto rows = structure_.magnetic->propagation_vectors;
    if (row < 0 || row >= static_cast<int>(rows.size())) {
        return false;
    }
    rows[static_cast<std::size_t>(row)].first = id.trimmed().toStdString();
    return replace(std::move(rows));
}

bool PropagationVectorListModel::setVector(int row, const QString& vector) {
    auto rows = structure_.magnetic->propagation_vectors;
    if (row < 0 || row >= static_cast<int>(rows.size())) {
        return false;
    }
    rows[static_cast<std::size_t>(row)].second = vector.trimmed().toStdString();
    return replace(std::move(rows));
}

void PropagationVectorListModel::append() {
    auto rows = structure_.magnetic->propagation_vectors;
    // The next free id and k = 0,0,0 for the user to edit: no vector the user did not enter (the owner, 2026-11-19).
    int n = static_cast<int>(rows.size()) + 1;
    const auto taken = [&rows](const std::string& id) {
        return std::any_of(rows.begin(), rows.end(), [&id](const auto& row) { return row.first == id; });
    };
    while (taken(std::to_string(n))) {
        ++n;
    }
    rows.emplace_back(std::to_string(n), "0,0,0");
    replace(std::move(rows));
}

void PropagationVectorListModel::remove(int row) {
    auto rows = structure_.magnetic->propagation_vectors;
    if (rows.size() <= 1 || row < 0 || row >= static_cast<int>(rows.size())) {
        return;
    }
    rows.erase(rows.begin() + row);
    replace(std::move(rows));
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

StructureViewModel::StructureViewModel(const SavedFile& saved, edi::Structure& structure, ProjectEditor& editor,
                                       ParameterRegistry& registry, QObject* parent)
    : QObject(parent),
      structure_(structure),
      editor_(editor),
      name_(QString::fromStdString(structure.name)),
      space_group_(new SpaceGroupViewModel(structure, editor, this)),
      cell_(new CellViewModel(structure, registry, this)),
      atom_sites_(new AtomSiteListModel(structure, editor, registry, this)),
      atom_site_adps_(new AtomSiteAdpListModel(structure, editor, registry, this)),
      atom_site_moments_(new AtomSiteMomentListModel(structure, editor, registry, this)),
      magnetic_form_factors_(new MagneticFormFactorListModel(structure, editor, registry, this)),
      propagation_vectors_(new PropagationVectorListModel(structure, editor, this)),
      scattering_lengths_(new ScatteringLengthListModel(structure, editor, this)),
      categories_(new CategoryListModel(this)),
      text_(new BlockText([saved, &structure] { return saved(std::filesystem::path(edi::entity_path("", "structure", structure.name)).generic_string()); }, this,
                          [&structure] { return std::filesystem::path(edi::entity_path("", "structure", structure.name)).generic_string(); }, {},
                          [saved, &structure] { return saved.discovered(std::filesystem::path(edi::entity_path("", "structure", structure.name)).generic_string()); })),
      calc_method_options_(new OptionListModel(this)) {
    categories_->setHidden(hidden_categories(structure_));
    categories_->setCategories(shown_categories(structure_), [this] { return text_->discoveryText().toStdString(); },
                               [this] { return edi::calculated_categories(structure_); });
    syncAtomTypes();
    syncCalcMethod();
    captureScene();
}

void StructureViewModel::captureScene() {
    scene_source_ = edi::capture_scene(structure_);
    emit sceneSourceChanged();
    emit bondsChanged();
}

void StructureViewModel::markSceneStale() {
    if (scene_source_.current) {
        scene_source_.current = false;
        emit sceneWentStale();  // the frame is the same: the view changes its `current` and nothing else
    }
}

void StructureViewModel::setName(const QString& name) {
    edi::Structure& structure = structure_;
    editor_.rename_structure(structure, name.toStdString());
}

MagneticGroupView StructureViewModel::magneticGroup() const {
    const crysta::MagneticGroupName& group = structure_.magnetic->group;
    // A file may give the BNS number without the UNI symbol; the field then shows the symbol of the table group the
    // selector shows, as a choice from the table would set it. The file keeps what it gave.
    std::string name_uni = group.name_uni;
    if (name_uni.empty() && !group.number_bns.empty()) {
        try {
            name_uni = crysta::magnetic_space_group(group.number_bns).name_uni;
        } catch (const std::invalid_argument&) {
            name_uni.clear();  // A number the table does not have shows no symbol.
        }
    }
    std::string setting, og_setting;
    for (const auto& row : structure_.magnetic->transforms) {
        if (row.second.source == "BNS") setting = row.second.pp_abc;
        if (row.second.source == "OG") og_setting = row.second.pp_abc;
    }
    // A file that gives no transform: the held setting's own (`a,b,c;0,0,0` for the BNS standard), never blank.
    if (setting.empty()) setting = edi::held_magnetic_setting(structure_);
    return MagneticGroupView{QString::fromStdString(group.number_bns), QString::fromStdString(group.name_bns),
                             QString::fromStdString(name_uni), QString::fromStdString(group.number_og),
                             QString::fromStdString(group.name_og), QString::fromStdString(group.point_group_name_uni),
                             QString::fromStdString(group.point_group_number_litvin), QString::fromStdString(setting),
                             QString::fromStdString(og_setting)};
}

QStringList StructureViewModel::magneticGroupNumbersBns() {
    static const QStringList numbers = [] {
        QStringList out;
        for (const crysta::MagneticSpaceGroupEntry& group : crysta::magnetic_space_groups())
            out.append(QString::fromStdString(group.number_bns));
        return out;
    }();
    return numbers;
}

QStringList StructureViewModel::magneticGroupNamesBns() {
    static const QStringList names = [] {
        QStringList out;
        for (const crysta::MagneticSpaceGroupEntry& group : crysta::magnetic_space_groups())
            out.append(QString::fromStdString(group.name_bns));
        return out;
    }();
    return names;
}

bool StructureViewModel::magnetic() const { return edi::structure_magnetic(structure_); }

namespace {
// Why the magnetic group gives no propagation vector; empty when it gives k = 0,0,0: no operation is a translation
// with time reversal (an anti-translation) and the magnetic cell is the parent's.
QString underived_propagation(const edi::MagneticDescription& magnetic) {
    const auto anti_translation = [](const std::string& text) {
        try {
            const crysta::MagneticOperation operation = crysta::parse_magnetic_operation(text);
            return operation.theta < 0 && operation.rotation == std::array<int, 9>{1, 0, 0, 0, 1, 0, 0, 0, 1} &&
                   operation.translation != std::array<double, 3>{};
        } catch (const std::invalid_argument&) {
            return false;
        }
    };
    for (const auto* rows : {&magnetic.operations, &magnetic.centerings}) {
        for (const auto& row : *rows) {
            if (anti_translation(row.second)) {
                return QObject::tr("k is not derived for a group with an anti-translation (type IV); give it here");
            }
        }
    }
    std::string child = magnetic.parent.child_transform_pp_abc;
    std::erase(child, ' ');
    if (!child.empty() && child != "a,b,c;0,0,0") {
        return QObject::tr("k is not derived: the magnetic cell is not the parent's (%1); give it here")
            .arg(QString::fromStdString(magnetic.parent.child_transform_pp_abc));
    }
    return {};
}
}  // namespace

QString StructureViewModel::derivedPropagationVector() const {
    const edi::MagneticDescription& magnetic = structure_.magnetic;
    if (!edi::structure_magnetic(structure_) || !magnetic.propagation_vectors.empty() || !underived_propagation(magnetic).isEmpty()) {
        return {};
    }
    return QStringLiteral("0,0,0");
}

QString StructureViewModel::propagationNotDerived() const {
    const edi::MagneticDescription& magnetic = structure_.magnetic;
    if (!edi::structure_magnetic(structure_) || !magnetic.propagation_vectors.empty()) return {};
    return underived_propagation(magnetic);
}

bool StructureViewModel::setMagnetic(bool magnetic) {
    const QString refusal = plain_refusal(editor_.apply(edi::Edit::structure_magnetic(structure_, magnetic), true));
    if (refusal != magnetic_group_refusal_) {
        magnetic_group_refusal_ = refusal;
        emit magneticGroupRefusalChanged();
    }
    return refusal.isEmpty();
}

QStringList StructureViewModel::magneticSettings() const {
    QStringList out;
    if (!edi::structure_magnetic(structure_)) return out;
    for (const std::string& transform : edi::magnetic_setting_transforms(structure_)) out.append(QString::fromStdString(transform));
    return out;
}

bool StructureViewModel::magneticSettingTabulated() const {
    return magneticSettings().contains(magneticGroup().setting);
}

bool StructureViewModel::chooseMagneticSetting(int index) {
    const QStringList settings = magneticSettings();
    if (index < 0 || index >= settings.size()) {
        return false;
    }
    const QString refusal = plain_refusal(
        editor_.apply(edi::Edit::magnetic_setting(structure_, settings.at(index).toStdString()), true));
    if (refusal != magnetic_group_refusal_) {
        magnetic_group_refusal_ = refusal;
        emit magneticGroupRefusalChanged();
    }
    return refusal.isEmpty();
}

QStringList StructureViewModel::magneticGroupNames() {
    static const QStringList names = [] {
        QStringList out;
        for (const crysta::MagneticSpaceGroupEntry& group : crysta::magnetic_space_groups()) {
            out.append(QString::fromStdString(group.number_bns + "  " + group.name_bns));
        }
        return out;
    }();
    return names;
}

bool StructureViewModel::setMagneticGroup(int index) {
    const std::vector<crysta::MagneticSpaceGroupEntry>& groups = crysta::magnetic_space_groups();
    if (index < 0 || index >= static_cast<int>(groups.size())) {
        return false;
    }
    const QString refusal = plain_refusal(editor_.apply(
        edi::Edit::magnetic_space_group(structure_, groups[static_cast<std::size_t>(index)].number_bns), true));
    if (refusal != magnetic_group_refusal_) {
        magnetic_group_refusal_ = refusal;
        emit magneticGroupRefusalChanged();
    }
    return refusal.isEmpty();
}

ParentGroupView StructureViewModel::parentGroup() const {
    const crysta::ParentSpaceGroup& parent = structure_.magnetic->parent;
    // The identity transform in either spelling a file uses.
    const auto identity = [](std::string text) {
        std::erase(text, ' ');
        return text.empty() || text == "a,b,c;0,0,0" || text == "a,b,c";
    };
    std::string own = structure_.space_group.name_h_m.value();
    std::string named = parent.name_h_m_alt;
    std::erase(own, ' ');
    std::erase(named, ' ');
    const bool differs = !parent.empty() && (!identity(parent.transform_pp_abc) || (!named.empty() && named != own));
    return ParentGroupView{QString::fromStdString(parent.name_h_m_alt), QString::fromStdString(parent.it_number),
                           QString::fromStdString(parent.transform_pp_abc), differs};
}

double StructureViewModel::minBondDistance() const {
    return structure_.geom.min_bond_distance_cutoff.get().value_or(edi::default_min_bond_distance_cutoff());
}

double StructureViewModel::bondDistanceIncrement() const {
    return structure_.geom.bond_distance_inc.get().value_or(edi::default_bond_distance_inc());
}

// A cutoff is a distance: a negative or non-finite one leaves it as it was.
void StructureViewModel::setMinBondDistance(double distance) {
    if (std::isfinite(distance) && distance >= 0.0 && distance != minBondDistance()) {
        editor_.apply(edi::Edit::assign(structure_.geom.min_bond_distance_cutoff, distance), true);
    }
    emit minBondDistanceChanged();
    emit bondsChanged();
}

void StructureViewModel::setBondDistanceIncrement(double increment) {
    if (std::isfinite(increment) && increment >= 0.0 && increment != bondDistanceIncrement()) {
        editor_.apply(edi::Edit::assign(structure_.geom.bond_distance_inc, increment), true);
    }
    emit bondDistanceIncrementChanged();
    emit bondsChanged();
}

QVariantList StructureViewModel::bonds() const {
    QVariantList out;
    if (!structure_.geometry_current()) {
        return out;
    }
    const edi::GeomBonds& bonds = structure_.geometry.geom_bond;
    for (std::size_t b = 0; b < bonds.size(); ++b) {
        out.append(QVariantMap{{QStringLiteral("site1"), QString::fromStdString(bonds.atom_site_label_1[b])},
                               {QStringLiteral("site2"), QString::fromStdString(bonds.atom_site_label_2[b])},
                               {QStringLiteral("symmetry1"), QString::fromStdString(bonds.site_symmetry_1[b])},
                               {QStringLiteral("symmetry2"), QString::fromStdString(bonds.site_symmetry_2[b])},
                               {QStringLiteral("distance"), bonds.distance[b]}});
    }
    return out;
}

void StructureViewModel::syncAtomTypes() {
    const edi::Project* project = editor_.currentProject();
    QStringList types;
    for (const std::string& type : project ? edi::atom_types(*project, structure_) : std::vector<std::string>{}) {
        types.append(QString::fromStdString(type));
    }
    if (types != atom_types_) {
        atom_types_ = types;
        emit atomTypesChanged();
    }
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
    atom_site_moments_->sync();
    magnetic_form_factors_->sync();
    propagation_vectors_->sync();
    scattering_lengths_->sync();
    emit magneticChanged();
    emit derivedPropagationVectorChanged();
    emit propagationNotDerivedChanged();
    emit magneticSettingsChanged();
    emit magneticSettingTabulatedChanged();
    emit magneticGroupChanged();
    emit parentGroupChanged();
    syncAtomTypes();
    emit minBondDistanceChanged();
    emit bondDistanceIncrementChanged();
    emit bondsChanged();
    syncCalcMethod();
    categories_->setHidden(hidden_categories(structure_));
    categories_->setCategories(shown_categories(structure_), [this] { return text_->discoveryText().toStdString(); },
                               [this] { return edi::calculated_categories(structure_); });
}

void StructureViewModel::syncCalcMethod() {
    // crysta's offer for this structure in the project as it is now (edi::calc_method_choice); outside a project the
    // structure's own method alone.
    const edi::Project* project = editor_.currentProject();
    edi::CalcMethodChoice choice;
    if (project != nullptr) {
        choice = edi::calc_method_choice(*project, structure_);
    } else {
        try {
            choice.current = edi::calc_method_token(structure_);
        } catch (const std::exception& error) {
            choice.current = structure_.calc_method.value();
            choice.reason = error.what();
        }
        choice.tokens = {choice.current};
    }
    // A Le Bail structure linked to a single crystal still shows its method, and the box offers Rietveld to leave it.
    if (std::find(choice.tokens.begin(), choice.tokens.end(), choice.current) == choice.tokens.end()) {
        choice.tokens.push_back(choice.current);
    }
    QStringList tokens;
    for (const std::string& token : choice.tokens) tokens.append(QString::fromStdString(token));
    if (tokens != calc_method_tokens_) {
        calc_method_tokens_ = tokens;
        calc_method_options_->setItemOptions("structure.calc_method", choice.tokens, "rietveld");
    }
    const QString method = QString::fromStdString(choice.current);
    if (method != calc_method_) {
        calc_method_ = method;
        emit calcMethodChanged();
    }
    const QString reason = QString::fromStdString(choice.reason);
    if (reason != calc_method_reason_) {
        calc_method_reason_ = reason;
        emit calcMethodReasonChanged();
    }
}

bool StructureViewModel::setCalcMethod(const QString& token) {
    QString refusal;
    if (token != calc_method_) {
        refusal = plain_refusal(editor_.apply_calc_method(structure_, token.toStdString()));
    }
    if (refusal != calc_method_refusal_) {
        calc_method_refusal_ = refusal;
        emit calcMethodRefusalChanged();
    }
    syncCalcMethod();
    return refusal.isEmpty();
}

}  // namespace edi_app
