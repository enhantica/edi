// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <QString>
#include <QStringView>

namespace edi_app {

// Where each control the assistant reaches lives: its page, its sidebar tab, its group (a category's
// `group.<category>` or a named group) and, for a row control, its table. Folded groups and table rows outside the view
// have no delegates, so a control is found by its id only after its page and tab are shown, its group opened and its
// row scrolled into view. The page, tab and group come from here alone.
// tools/checks/assistant_control_routes.py checks each place against the QML that declares the control.
struct ControlRoute {
    const char* prefix;  // the id, or its start up to and including a dot
    const char* page;    // project, structure, experiment or analysis; empty: not on one page
    const char* tab;     // the page's sidebar tab, basic (Main) or extras (Extra); empty with no page
    const char* group;   // empty: the control is outside any group (a tab, a dialog field)
    const char* table;   // empty: not a row control
};

inline constexpr ControlRoute kControlRoutes[] = {
    {"appBar.tab.", "", "", "", ""},
    {"sideBar.tab.", "", "", "", ""},
    {"project.create", "project", "basic", "group.getStarted", ""},
    {"createProject.", "project", "basic", "", ""},
    {"structures.", "structure", "basic", "group.structures", "structures.list"},
    {"spaceGroup.", "structure", "basic", "group.space_group", ""},
    {"cell.", "structure", "basic", "group.cell", ""},
    {"atomSiteAdp.", "structure", "basic", "group.atom_site_aniso", "atomSiteAdps.list"},
    {"atomSiteAdps.", "structure", "basic", "group.atom_site_aniso", "atomSiteAdps.list"},
    {"atomSites.", "structure", "basic", "group.atom_site", "atomSites.list"},
    {"atomSite.", "structure", "basic", "group.atom_site", "atomSites.list"},
    {"experiments.", "experiment", "basic", "group.experiments", "experiments.list"},
    {"experimentType.", "experiment", "basic", "group.experiments", ""},
    {"linkedStructure.", "experiment", "basic", "group.linked_structure", "linkedStructure.list"},
    {"excludedRegions.", "experiment", "basic", "group.excluded_region", "excludedRegions.list"},
    {"excludedRegion.", "experiment", "basic", "group.excluded_region", "excludedRegions.list"},
    {"instrument.", "experiment", "basic", "group.instrument", ""},
    {"peak.", "experiment", "basic", "group.peak", ""},
    {"peak.cutoff_fwhm", "experiment", "extras", "group.peak", ""},
    {"background.", "experiment", "basic", "group.background", ""},
    {"extinction.", "experiment", "basic", "group.extinction", ""},
    {"absorption.", "experiment", "extras", "group.absorption", ""},
    {"jointFit.", "analysis", "extras", "group.joint_fit", "jointFit.list"},
    {"parameters.", "analysis", "basic", "group.parameters", "parameters.list"},
    {"relations.aliases", "analysis", "extras", "group.alias", ""},
    {"aliases.", "analysis", "extras", "group.alias", "aliases.list"},
    {"alias.", "analysis", "extras", "group.alias", "aliases.list"},
    {"relations.constraints", "analysis", "extras", "group.constraint", ""},
    {"constraints.", "analysis", "extras", "group.constraint", "constraints.list"},
    {"constraint.", "analysis", "extras", "group.constraint", "constraints.list"},
    {"statusBar.fit.button", "", "", "", ""},
    // The search field of an open searchable list (the alias target's): in its popup, outside any group.
    {"comboBox.search", "", "", "", ""},
};

// The route of a control id: the longest matching prefix, or nullptr for an id the table does not know.
inline const ControlRoute* control_route(QStringView id) {
    const ControlRoute* best = nullptr;
    qsizetype length = -1;
    for (const ControlRoute& route : kControlRoutes) {
        const auto prefix = QLatin1StringView(route.prefix);
        const bool inside = id.startsWith(prefix) &&
                            (id.size() == prefix.size() || prefix.endsWith(QLatin1Char('.')) || id.at(prefix.size()) == QLatin1Char('.'));
        if (inside && prefix.size() > length) {
            best = &route;
            length = prefix.size();
        }
    }
    return best;
}

// The route of a category's own fields, or nullptr for a category that has no group of its own here.
inline const ControlRoute* category_route(QStringView category) {
    constexpr QLatin1StringView start("group.");
    for (const ControlRoute& route : kControlRoutes) {
        const QLatin1StringView group(route.group);
        if (QLatin1StringView(route.prefix).endsWith(QLatin1Char('.')) && group.startsWith(start) && group.sliced(start.size()) == category)
            return &route;
    }
    return nullptr;
}

// The tier whose groups a tab lists (CategoryGroup's shownTier).
inline QLatin1StringView route_tier(const ControlRoute& route) {
    return QLatin1StringView(QLatin1StringView(route.tab) == QLatin1StringView("extras") ? "Extras" : "Basic");
}

// Whether two routes lead to the same group of one tab of one page.
inline bool same_place(const ControlRoute& a, const ControlRoute& b) {
    return QLatin1StringView(a.page) == QLatin1StringView(b.page) && QLatin1StringView(a.tab) == QLatin1StringView(b.tab) &&
           QLatin1StringView(a.group) == QLatin1StringView(b.group);
}

}  // namespace edi_app
