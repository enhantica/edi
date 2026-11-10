// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_STRUCTURE_INSTANCES_HPP
#define EDI_APP_STRUCTURE_INSTANCES_HPP

#include <QByteArray>
#include <QColor>
#include <QtQml/qqmlregistration.h>
#include <QtQuick3D/QQuick3DInstancing>
#include <optional>
#include <vector>

#include "edi/structure_scene.hpp"

namespace edi_app {

// One instance table of the structure view (edi ADR-0017 §16, ADR-0022 §7): the entries the core's
// edi::scene_drawing returns for one mesh, packed into Qt Quick 3D's instance buffer in C++ — one draw call for
// the mesh, whatever the number of entries, as Qt's instanced-rendering guidance has it. The buffer is packed
// once per presentation, returned unchanged until the next one, and marked dirty exactly then: a pointer event
// moves the camera and never touches a table. Depth sorting and transparency stay off.
class StructureInstances : public QQuick3DInstancing {
    Q_OBJECT
    QML_ELEMENT
    Q_PROPERTY(int count READ count NOTIFY countChanged)

   public:
    explicit StructureInstances(QQuick3DObject* parent = nullptr);

    // Replaces the table. `color`, when set, replaces every entry's colour from `first` on (the cell edges
    // take the theme's foreground colour).
    void setEntries(const std::vector<edi::SceneInstance>& entries, std::size_t first = 0,
                    std::optional<QColor> color = std::nullopt);
    int count() const { return count_; }

   signals:
    void countChanged();

   protected:
    QByteArray getInstanceBuffer(int* instanceCount) override;

   private:
    QByteArray buffer_;
    int count_ = 0;
};

}  // namespace edi_app

#endif  // EDI_APP_STRUCTURE_INSTANCES_HPP
