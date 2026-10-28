// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_PARAMETER_REGISTRY_HPP
#define EDI_APP_PARAMETER_REGISTRY_HPP

#include <QList>
#include <QObject>
#include <map>
#include <memory>
#include <vector>
#include "edi/calculation.hpp"
#include <unordered_map>
#include <unordered_set>
#include <string>
#include <utility>

#include "edi/model.hpp"

namespace edi_app {

class ParameterItem;
class ProjectEditor;

// The one ParameterItem per shown core parameter, in page order, from the core's parameter_entries, and one per
// descriptor that is no parameter (model_descriptors), after its category's parameters.
// `rebuild` re-derives the set after a structural change, keeping the item of every parameter still
// shown; `publish` sends each item's differences after any change (I3), and first reads again what
// an item shows of the model beside its parameter (an atom's element, and whether the space group
// leaves the parameter refinable, edi ADR-0019).
class ParameterRegistry : public QObject {
    Q_OBJECT

   public:
    ParameterRegistry(ProjectEditor& editor, QObject* parent);

    void rebuild(edi::Project& project);
    void publish(edi::Project& project);
    const QList<ParameterItem*>& items() const { return items_; }
    ParameterItem* find(const edi::Parameter* parameter) const;
    // Whether these already-published fileValue/fileSu pairs describe this exact
    // live owner. Inspection never recalculates its save-spelling decision.
    bool fileTextCurrent(const edi::Project& project) const noexcept;

   signals:
    // After a rebuild that added or removed items; removed ones are deleted later.
    void itemsChanged();

   private:
    struct FileTextPublication {
        const edi::Project* project=nullptr;
        edi::WorkStamps stamps;
        std::string rule;
        std::vector<std::pair<std::shared_ptr<const edi::detail::ComputedSource>,bool>> calculations;
        bool ready=false;
    };
    std::shared_ptr<FileTextPublication> beginFileText(const edi::Project& project) noexcept;
    void finishFileText(const std::shared_ptr<FileTextPublication>& publication,const edi::Project& project) noexcept;
    bool matchesFileText(const FileTextPublication& publication,const edi::Project& project) const;
    std::shared_ptr<FileTextPublication> file_text_publication_;
    std::size_t file_text_publication_depth_=0;
    void refreshElements(const edi::Project& project);
    void refreshRefinable(edi::Project& project);
    void refreshFittability(edi::Project& project);
    void refreshEstimated(const edi::Project& project);
    void refreshSpelling(const edi::Project& project);
    void refreshDefiniteness(const edi::Project& project);
    ProjectEditor& editor_;
    QList<ParameterItem*> items_;
    std::map<std::pair<const edi::Parameter*, std::string>, ParameterItem*> by_key_;
    std::unordered_map<const edi::Parameter*, ParameterItem*> by_parameter_;
};

}  // namespace edi_app

#endif  // EDI_APP_PARAMETER_REGISTRY_HPP
