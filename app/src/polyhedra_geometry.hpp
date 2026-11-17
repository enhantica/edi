// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_POLYHEDRA_GEOMETRY_HPP
#define EDI_APP_POLYHEDRA_GEOMETRY_HPP

#include <QtQml/qqmlregistration.h>
#include <QtQuick3D/QQuick3DGeometry>

#include "edi/structure_scene.hpp"

namespace edi_app {

// The structure view's coordination polyhedra as one mesh (edi ADR-0022 §9): each face flat, in its polyhedron's
// colour as a vertex colour in linear light, as the shared sites' are. The material sets the opacity.
class PolyhedraGeometry : public QQuick3DGeometry {
    Q_OBJECT
    QML_ELEMENT
    Q_PROPERTY(int count READ count NOTIFY countChanged)

   public:
    explicit PolyhedraGeometry(QQuick3DObject* parent = nullptr);

    void setPolyhedra(const edi::StructureScene& scene);
    int count() const { return count_; }

   signals:
    void countChanged();

   private:
    int count_ = 0;
};

}  // namespace edi_app

#endif  // EDI_APP_POLYHEDRA_GEOMETRY_HPP
