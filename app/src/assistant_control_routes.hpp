// SPDX-License-Identifier: BSD-3-Clause
#pragma once

#include <QString>
#include <QStringView>

namespace edi_app {

// Where each control the assistant reaches lives: its page, its group (a category's `group.<category>` or a named
// group) and, for a row control, its table. Folded groups and table rows outside the view have no delegates, so a
// control is found by its id only after its page is shown, its group opened and its row scrolled into view.
// tools/checks/assistant_control_routes.py checks every id the assistant uses against this table and the QML.
struct ControlRoute {
    const char* prefix;  // the id, or its start up to and including a dot
    const char* page;    // project, structure, experiment or analysis
    const char* group;   // empty: the control is outside any group (a page tab, a dialog field)
    const char* table;   // empty: not a row control
};

inline constexpr ControlRoute kControlRoutes[] = {
    {"appBar.tab.", "", "", ""},
    {"sideBar.tab.", "", "", ""},
    {"project.create", "project", "", ""},
    {"createProject.", "project", "", ""},
    {"structures.", "structure", "group.structures", "structures.list"},
    {"spaceGroup.", "structure", "group.space_group", ""},
    {"atomSiteAdp.", "structure", "group.atom_site_aniso", "atomSiteAdps.list"},
    {"atomSites.", "structure", "group.atom_site", "atomSites.list"},
    {"atomSite.", "structure", "group.atom_site", "atomSites.list"},
    {"experiments.", "experiment", "group.experiments", "experiments.list"},
    {"experimentType.", "experiment", "group.experiments", ""},
    {"linkedStructure.", "experiment", "group.linked_structure", "linkedStructure.list"},
    {"excludedRegions.", "experiment", "group.excluded_region", "excludedRegions.list"},
    {"excludedRegion.", "experiment", "group.excluded_region", "excludedRegions.list"},
    {"instrument.", "experiment", "group.instrument", ""},
    {"peak.", "experiment", "group.peak", ""},
    {"background.", "experiment", "group.background", ""},
    {"extinction.", "experiment", "group.extinction", ""},
    {"absorption.", "experiment", "group.absorption", ""},
    {"jointFit.weight.", "analysis", "group.joint_fit", "jointFit.list"},
    {"parameters.", "analysis", "group.parameters", "parameters.list"},
    {"relations.aliases", "analysis", "relations.aliases", ""},
    {"aliases.", "analysis", "relations.aliases", "aliases.list"},
    {"alias.", "analysis", "relations.aliases", "aliases.list"},
    {"relations.constraints", "analysis", "relations.constraints", ""},
    {"constraints.", "analysis", "relations.constraints", "constraints.list"},
    {"constraint.", "analysis", "relations.constraints", "constraints.list"},
};

// The route of a control id: the longest matching prefix, or nullptr for an id the table does not know.
inline const ControlRoute* control_route(QStringView id) {
    const ControlRoute* best = nullptr;
    qsizetype length = -1;
    for (const ControlRoute& route : kControlRoutes) {
        const auto prefix = QLatin1StringView(route.prefix);
        if ((id == prefix || (prefix.endsWith(QLatin1Char('.')) && id.startsWith(prefix))) && prefix.size() > length) {
            best = &route;
            length = prefix.size();
        }
    }
    return best;
}

}  // namespace edi_app
