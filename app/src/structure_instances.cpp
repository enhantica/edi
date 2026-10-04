// SPDX-License-Identifier: BSD-3-Clause
#include "structure_instances.hpp"

#include <QQuaternion>
#include <QVector3D>

namespace edi_app {

StructureInstances::StructureInstances(QQuick3DObject* parent) : QQuick3DInstancing(parent) {}

void StructureInstances::setEntries(const std::vector<edi::SceneInstance>& entries, std::size_t first,
                                    std::optional<QColor> color) {
    QByteArray buffer;
    buffer.resize(static_cast<qsizetype>(entries.size() * sizeof(InstanceTableEntry)));
    auto* out = reinterpret_cast<InstanceTableEntry*>(buffer.data());
    for (std::size_t i = 0; i != entries.size(); ++i) {
        const edi::SceneInstance& entry = entries[i];
        const QColor shade = color && i >= first ? *color : QColor(entry.color.r, entry.color.g, entry.color.b);
        out[i] = calculateTableEntryFromQuaternion(
            QVector3D(static_cast<float>(entry.position.x), static_cast<float>(entry.position.y),
                      static_cast<float>(entry.position.z)),
            QVector3D(static_cast<float>(entry.scale.x), static_cast<float>(entry.scale.y),
                      static_cast<float>(entry.scale.z)),
            QQuaternion(static_cast<float>(entry.rotation[0]), static_cast<float>(entry.rotation[1]),
                        static_cast<float>(entry.rotation[2]), static_cast<float>(entry.rotation[3])),
            shade);
    }
    buffer_ = std::move(buffer);
    const int count = static_cast<int>(entries.size());
    const bool counted = count != count_;
    count_ = count;
    markDirty();
    if (counted) {
        emit countChanged();
    }
}

QByteArray StructureInstances::getInstanceBuffer(int* instanceCount) {
    if (instanceCount != nullptr) {
        *instanceCount = count_;
    }
    return buffer_;
}

}  // namespace edi_app
