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

void SpaceGroupViewModel::setNameHM(const QString& name) {
    edi::SpaceGroup& group = structure_.space_group;
    const std::string typed = name.toStdString();
    if (edi::same_space_group_name(typed, group.name_h_m)) {
        return;  // the same group: its code stays as chosen
    }
    const std::optional<edi::SpaceGroupSettingName> setting = edi::space_group_setting_for_name(typed);
    editor_.apply_creation_control(setting ? edi::Edit::space_group_setting(group, *setting, false) : edi::Edit::assign(group.name_h_m, typed),
                  false,{ProjectEditor::CreationAction::Kind::SpaceGroupName,&structure_,{},name});
}

void SpaceGroupViewModel::setCoordSystemCode(const QString& code) {
    edi::SpaceGroup& group = structure_.space_group;
    const std::string chosen = code.toStdString();
    const std::optional<edi::SpaceGroupSettingName> setting = edi::space_group_setting_for_code(it_number_, chosen);
    editor_.apply_creation_control(setting ? edi::Edit::space_group_setting(group, *setting, false)
                          : edi::Edit::assign(group.coord_system_code, chosen),
                  false,{ProjectEditor::CreationAction::Kind::SpaceGroupSetting,&structure_,{},code});
}

void SpaceGroupViewModel::setItNumber(int number) {
    if (number > 230) {
        return;  // no such space-group type: never stored
    }
    edi::SpaceGroup& group = structure_.space_group;
    const std::optional<edi::SpaceGroupSettingName> setting =
        number > 0 ? edi::space_group_setting_for_number(number) : std::nullopt;
    editor_.apply_creation_control(setting ? edi::Edit::space_group_setting(group, *setting, true)
                          : edi::Edit::assign(group.it_number, number > 0 ? std::optional<int>(number) : std::nullopt),
                  false,{ProjectEditor::CreationAction::Kind::SpaceGroupNumber,&structure_,{},{},static_cast<double>(number)});
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
    for (const auto& site : structure_.atom_sites) {
        rows.append({site.get(),
                     {QString::fromStdString(site->id), QString::fromStdString(site->type_symbol),
                      QString::fromStdString(site->wyckoff_letter), QString::fromStdString(site->adp_type),
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
                           : role == QLatin1String("typeSymbol")      ? edi::Edit::assign(site->type_symbol, text)
                           : role == QLatin1String("wyckoffLetter")   ? edi::Edit::assign(site->wyckoff_letter, text)
                                                                      : edi::Edit::adp_type(structure, *site, text);
    // A type change can add or remove a tensor row, which changes the parameter set.
    return editor_.apply_creation_control(edit, label || role == QLatin1String("adpType"),
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
    editor_.apply_creation_control(edi::Edit::append(structure.atom_sites, std::move(site)), true, action);
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
        {ProjectEditor::CreationAction::Kind::AtomRemove,keyAt(row)});
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
    for (const auto& site : structure_.atom_sites) {
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

AtomSiteMomentListModel::AtomSiteMomentListModel(edi::Structure& structure, ProjectEditor& editor,
                                                 ParameterRegistry& registry, QObject* parent)
    : RowTableModel({"label", "ion", "mx", "my", "mz", "symmform"}, parent),
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
        rows.append({site.get(), values});
    }
    setTableRows(rows);
    ++revision_;
    emit revisionChanged();
}

QStringList AtomSiteMomentListModel::ions(int row) const {
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
        const std::string ion = declared != nullptr && !declared->ion.value().empty() ? declared->ion.value()
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

// A symmetry form's components as combinations of the free ones (`Mx,-Mx,0`: y = -x), row k column s. A term
// that does not parse leaves the component as its own.
std::array<std::array<double, 3>, 3> tie_matrix(const std::string& symmform) {
    std::array<std::array<double, 3>, 3> out{{{1, 0, 0}, {0, 1, 0}, {0, 0, 1}}};
    std::vector<std::string> parts;
    std::string part;
    for (const char ch : symmform) {
        if (ch == ',') {
            parts.push_back(part);
            part.clear();
        } else if (ch != ' ') {
            part += ch;
        }
    }
    parts.push_back(part);
    if (parts.size() != 3) {
        return out;
    }
    for (std::size_t k = 0; k < 3; ++k) {
        std::array<double, 3> row{};
        const std::string& text = parts[k];
        std::size_t at = 0;
        bool parsed = true;
        while (at < text.size() && parsed) {
            std::size_t end = at + 1;
            while (end < text.size() && text[end] != '+' && text[end] != '-') {
                ++end;
            }
            std::string term = text.substr(at, end - at);
            at = end;
            if (term == "0" || term == "+0" || term == "-0") {
                continue;
            }
            const std::size_t m = term.find('M');
            if (m == std::string::npos || m + 2 != term.size() || term[m + 1] < 'x' || term[m + 1] > 'z') {
                parsed = false;
                break;
            }
            std::string coefficient = term.substr(0, m);
            if (coefficient.empty() || coefficient == "+") {
                coefficient = "1";
            } else if (coefficient == "-") {
                coefficient = "-1";
            }
            try {
                row[static_cast<std::size_t>(term[m + 1] - 'x')] += std::stod(coefficient);
            } catch (const std::exception&) {
                parsed = false;
            }
        }
        if (parsed) {
            out[k] = row;
        }
    }
    return out;
}

// After a fit, the covariance of a moment's crystal-axis components and its structure's cell, from the parameters'
// s.u. and the fit's correlations (edi ADR-0070); none before a fit. A tied component follows its free ones through the symmetry form.
std::optional<std::array<double, 81>> moment_covariance(const edi::Project* project, const edi::Structure& structure,
                                                        const edi::AtomSiteMoment& moment) {
    if (project == nullptr || !project->fit_result.held()) {
        return std::nullopt;
    }
    std::map<std::pair<std::string, std::string>, double> correlation;
    for (const auto& row : project->fit_result.correlations) {
        if (row->file_path.empty()) {
            correlation[{row->parameter_unique_name_i.value(), row->parameter_unique_name_j.value()}] = row->correlation.get();
        }
    }
    if (correlation.empty()) {
        return std::nullopt;
    }
    const std::string block = structure.name.value();
    const std::string site = moment.id.value();
    const edi::Cell& cell = structure.cell;
    // The nine inputs: the free components (as their own symbols), then the cell.
    const std::array<const edi::Parameter*, 9> inputs{&moment.crystalaxis_x, &moment.crystalaxis_y, &moment.crystalaxis_z,
                                                      &cell.length_a,        &cell.length_b,        &cell.length_c,
                                                      &cell.angle_alpha,     &cell.angle_beta,      &cell.angle_gamma};
    const std::array<std::string, 9> names{
        block + ".atom_site_moment." + site + ".crystalaxis_x", block + ".atom_site_moment." + site + ".crystalaxis_y",
        block + ".atom_site_moment." + site + ".crystalaxis_z", block + ".cell.length_a",
        block + ".cell.length_b", block + ".cell.length_c", block + ".cell.angle_alpha",
        block + ".cell.angle_beta", block + ".cell.angle_gamma"};
    const std::array<std::array<double, 3>, 3> ties = tie_matrix(moment.symmform);
    std::array<double, 81> free{};
    for (std::size_t i = 0; i < 9; ++i) {
        const bool tied = i < 3 && (ties[i][i] != 1.0 || ties[i][(i + 1) % 3] != 0.0 || ties[i][(i + 2) % 3] != 0.0);
        const double sigma_i = !tied && inputs[i]->uncertainty.has_value() ? *inputs[i]->uncertainty : 0.0;
        for (std::size_t j = 0; j < 9; ++j) {
            const bool tied_j = j < 3 && (ties[j][j] != 1.0 || ties[j][(j + 1) % 3] != 0.0 || ties[j][(j + 2) % 3] != 0.0);
            const double sigma_j = !tied_j && inputs[j]->uncertainty.has_value() ? *inputs[j]->uncertainty : 0.0;
            double rho = i == j ? 1.0 : 0.0;
            if (i != j) {
                const auto found = correlation.find({names[i], names[j]});
                const auto other = correlation.find({names[j], names[i]});
                rho = found != correlation.end() ? found->second : other != correlation.end() ? other->second : 0.0;
            }
            free[9 * i + j] = rho * sigma_i * sigma_j;
        }
    }
    // The components' covariance through the ties: T over the moment block, the identity over the cell.
    std::array<std::array<double, 9>, 9> t{};
    for (std::size_t k = 0; k < 3; ++k) {
        for (std::size_t s = 0; s < 3; ++s) {
            t[k][s] = ties[k][s];
        }
    }
    for (std::size_t c = 3; c < 9; ++c) {
        t[c][c] = 1.0;
    }
    std::array<double, 81> out{};
    for (std::size_t i = 0; i < 9; ++i) {
        for (std::size_t j = 0; j < 9; ++j) {
            double sum = 0.0;
            for (std::size_t a = 0; a < 9; ++a) {
                for (std::size_t b = 0; b < 9; ++b) {
                    sum += t[i][a] * free[9 * a + b] * t[j][b];
                }
            }
            out[9 * i + j] = sum;
        }
    }
    return out;
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

std::array<double, 3> from_form(const std::array<double, 6>& cell, const std::array<double, 3>& values,
                                const QString& form) {
    if (form == QLatin1String("cartesian")) {
        return crysta::moment_crystal_axis(cell, values);
    }
    if (form == QLatin1String("spherical")) {
        return crysta::moment_crystal_axis(cell, crysta::moment_from_spherical(values));
    }
    return values;
}
}  // namespace

QVariantList AtomSiteMomentListModel::components(int row, const QString& form) const {
    const auto* site = static_cast<const edi::AtomSite*>(keyAt(row));
    const edi::AtomSiteMoment* moment = moment_of(structure_, site);
    if (moment == nullptr) {
        return {};
    }
    const std::array<double, 6> cell = cell_of(structure_);
    const std::array<double, 3> crystal{moment->crystalaxis_x.value, moment->crystalaxis_y.value,
                                        moment->crystalaxis_z.value};
    const bool has_su = moment->crystalaxis_x.uncertainty.has_value() ||
                        moment->crystalaxis_y.uncertainty.has_value() ||
                        moment->crystalaxis_z.uncertainty.has_value();
    const std::array<double, 3> su{moment->crystalaxis_x.uncertainty.value_or(0.0),
                                   moment->crystalaxis_y.uncertainty.value_or(0.0),
                                   moment->crystalaxis_z.uncertainty.value_or(0.0)};
    const std::array<double, 3> values = in_form(cell, crystal, form);
    const std::array<double, 3> spherical = crysta::moment_spherical(crysta::moment_cartesian(cell, crystal));
    std::array<double, 3> spherical_su = crysta::moment_spherical_su(cell, crystal, su);
    std::array<double, 3> values_su = su;
    if (form == QLatin1String("cartesian")) {
        values_su = crysta::moment_cartesian_su(cell, su);
    } else if (form == QLatin1String("spherical")) {
        values_su = spherical_su;
    }
    // After a fit the s.u. come from its covariance, correlations and the cell included.
    const std::optional<std::array<double, 81>> covariance = moment_covariance(editor_.currentProject(), structure_, *moment);
    if (covariance.has_value() && has_su) {
        const std::array<double, 4> fitted = crysta::moment_form_su(cell, crystal, form.toStdString(), *covariance);
        values_su = {fitted[0], fitted[1], fitted[2]};
        spherical_su[0] = fitted[3];
    }
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
    QVariantList out;
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
    out.append(covariance.has_value() && has_su);
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
        // The core decides what the symmetry admits; only the free components are written, the others follow.
        const edi::MomentEdit edit =
            edi::moment_edit(structure_, *moment, form.toStdString(), static_cast<std::size_t>(k), value);
        refusal = QString::fromStdString(edit.refusal);
        if (refusal.isEmpty()) {
            const std::vector<edi::Parameter*> components = const_cast<edi::AtomSiteMoment*>(moment)->parameters();
            std::vector<std::pair<edi::Parameter*, double>> writes;
            for (std::size_t i = 0; i < components.size(); ++i) {
                const ParameterItem* item = registry_.find(components[i]);
                if (item != nullptr && item->isRefinable()) {
                    writes.emplace_back(components[i], edit.crystal[i]);
                }
            }
            refusal = writes.empty() ? tr("The site symmetry fixes this moment")
                                     : editor_.apply(edi::Edit::values(std::move(writes)), false);
        }
    }
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
    const QString refusal = editor_.apply(edi::Edit::propagation_vectors(structure, std::move(rows)), true);
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
    // The next free id, and a half-order vector along a to start from; crysta refuses it with its reason
    // when the cell and the group cannot carry it.
    int n = static_cast<int>(rows.size()) + 1;
    const auto taken = [&rows](const std::string& id) {
        return std::any_of(rows.begin(), rows.end(), [&id](const auto& row) { return row.first == id; });
    };
    while (taken(std::to_string(n))) {
        ++n;
    }
    rows.emplace_back(std::to_string(n), "1/2,0,0");
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

StructureViewModel::StructureViewModel(SavedFile saved, edi::Structure& structure, ProjectEditor& editor,
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
                          [saved, &structure] { return saved.discovered(std::filesystem::path(edi::entity_path("", "structure", structure.name)).generic_string()); })) {
    categories_->setCategories(edi::structure_categories(structure_), [this] { return text_->discoveryText().toStdString(); },
                               [this] { return edi::calculated_categories(structure_); });
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
    editor_.rename_structure(structure, name.toStdString());
}

QVariantMap StructureViewModel::magneticGroup() const {
    const crysta::MagneticGroupName& group = structure_.magnetic->group;
    return {{QStringLiteral("number_bns"), QString::fromStdString(group.number_bns)},
            {QStringLiteral("name_bns"), QString::fromStdString(group.name_bns)},
            {QStringLiteral("name_uni"), QString::fromStdString(group.name_uni)},
            {QStringLiteral("number_og"), QString::fromStdString(group.number_og)},
            {QStringLiteral("name_og"), QString::fromStdString(group.name_og)}};
}

QVariantMap StructureViewModel::parentGroup() const {
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
    return {{QStringLiteral("name_h_m_alt"), QString::fromStdString(parent.name_h_m_alt)},
            {QStringLiteral("it_number"), QString::fromStdString(parent.it_number)},
            {QStringLiteral("transform_pp_abc"), QString::fromStdString(parent.transform_pp_abc)},
            {QStringLiteral("differs"), differs}};
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
    emit magneticGroupChanged();
    emit parentGroupChanged();
    categories_->setCategories(edi::structure_categories(structure_), [this] { return text_->discoveryText().toStdString(); },
                               [this] { return edi::calculated_categories(structure_); });
}

}  // namespace edi_app
