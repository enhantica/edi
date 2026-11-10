// SPDX-License-Identifier: BSD-3-Clause
#ifndef EDI_APP_SHARED_SITE_GEOMETRY_HPP
#define EDI_APP_SHARED_SITE_GEOMETRY_HPP

#include <QtQml/qqmlregistration.h>
#include <QtQuick3D/QQuick3DGeometry>

#include "edi/structure_scene.hpp"

namespace edi_app {

// The drawn shared sites of the structure view, as one mesh (edi ADR-0017 §16, ADR-0022 §3, §7): each site's
// sphere cut into wedges about the home view's direction, each wedge spanning its part's fraction of the turn in
// the part's colour, the first starting at the plane through that axis and the home view's up, as
// diffraction-lib's OccupancyWedgeSphere. A wedge of fraction 0 has no triangle. Every vertex of the site with
// ordinal k (SceneDrawing::shared[k]) carries the texture coordinate (k + 0.5, 0), so a pick names the site
// whose surface was hit. Colours are vertex colours, in linear light as the instance colours are.
class SharedSiteGeometry : public QQuick3DGeometry {
    Q_OBJECT
    QML_ELEMENT
    Q_PROPERTY(int siteCount READ siteCount NOTIFY siteCountChanged)

   public:
    explicit SharedSiteGeometry(QQuick3DObject* parent = nullptr);

    void setSites(const edi::StructureScene& scene, const edi::SceneDrawing& drawing, int segments, int rings);
    int siteCount() const { return site_count_; }

   signals:
    void siteCountChanged();

   private:
    int site_count_ = 0;
};

}  // namespace edi_app

#endif  // EDI_APP_SHARED_SITE_GEOMETRY_HPP
