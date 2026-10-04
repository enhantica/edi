// SPDX-License-Identifier: BSD-3-Clause
pragma ComponentBehavior: Bound

import QtQuick
import QtQuick3D
import QtQuick3D.Helpers

import edi.app

// The structure view's 3D scene (edi ADR-0017 §16): the instance tables the controller fills from C++
// (spheres, cylinders, the triad's shafts and heads), the shared sites' mesh, their models and materials, and
// the camera whose matrices are the core's projection, with the lights that move with it. The scene always
// exists, so the view's state is the same on every platform; StructureView's View3D, created only where Qt
// Quick draws through a 3D API, imports it.
Node {
    id: scene

    property StructureViewController controller: null
    readonly property StructureInstances spheres: spheresTable
    readonly property StructureInstances cylinders: cylindersTable
    readonly property StructureInstances triadShafts: shaftsTable
    readonly property StructureInstances triadHeads: headsTable
    readonly property SharedSiteGeometry shared: sharedGeometry
    // The orthographic projection through Qt's orthographic camera, the perspective one (with its screen pan)
    // through a custom camera: both are the core's projection, and Qt picks parallel rays in the first.
    readonly property Camera camera: scene.controller && scene.controller.projection === "perspective" ? perspectiveCamera : orthographicCamera

    // The text for a pick: a sphere by its instance, a shared site by the texture coordinate its
    // triangles carry.
    function hoverText(result) {
        if (result.objectHit === spheresModel)
            return scene.controller.hoverAtSphere(result.instanceIndex);
        if (result.objectHit === sharedModel)
            return scene.controller.hoverAtShared(result.uvPosition.x);
        return "";
    }

    // The core's projection (edi::project) as the camera's own matrices; the lights move with it, each shining
    // from its camera-local direction, as diffraction-lib's headlights. The style table's light values are
    // diffraction-lib's three.js intensities, whose physical units carry the Lambert 1/π; Qt's brightness is that
    // intensity × 1.5/π, calibrated (with StructureView's linear tone mapping, sRGB out) so that each element's
    // median colour in the capture of lbco is within about ten levels of diffraction-lib's render (ADR-0017 §16).
    readonly property real lightScale: 1.5 / Math.PI
    // diffraction-lib's Phong highlight (specular 0.2, shininess 90) has no one-to-one counterpart in Qt's
    // principled shading: a dielectric with roughness 0.25 and specular amount 1, matched by eye on cosio to the
    // render's small, soft spot up and to the right of every sphere's centre, on the instanced spheres, the bonds
    // and the shared sites' wedges alike (ADR-0017 §16).
    readonly property real roughness: 0.25
    readonly property real specularAmount: 1

    OrthographicCamera {
        id: orthographicCamera

        position: scene.controller.cameraPosition
        rotation: scene.controller.cameraRotation
        horizontalMagnification: scene.controller.orthographicMagnification
        verticalMagnification: scene.controller.orthographicMagnification
        clipNear: 1
        clipFar: scene.controller.cameraClipFar
    }
    CustomCamera {
        id: perspectiveCamera

        position: scene.controller.cameraPosition
        rotation: scene.controller.cameraRotation
        projection: scene.controller.cameraProjection
    }
    // The lights follow the camera, whichever is drawing.
    Node {
        rotation: scene.controller.cameraRotation

        DirectionalLight {
            objectName: "structure.view.light.key"
            rotation: scene.controller.keyLightRotation
            brightness: scene.controller.keyLight * scene.lightScale
            ambientColor: Qt.rgba(scene.controller.ambientLight * scene.lightScale, scene.controller.ambientLight * scene.lightScale, scene.controller.ambientLight * scene.lightScale, 1)
        }
        DirectionalLight {
            objectName: "structure.view.light.fill"
            rotation: scene.controller.fillLightRotation
            brightness: scene.controller.fillLight * scene.lightScale
        }
    }

    StructureInstances {
        id: spheresTable

        objectName: "structure.view.spheres"
    }
    StructureInstances {
        id: cylindersTable

        objectName: "structure.view.cylinders"
    }
    StructureInstances {
        id: shaftsTable

        objectName: "structure.view.triad.shafts"
    }
    StructureInstances {
        id: headsTable

        objectName: "structure.view.triad.heads"
    }

    PrincipledMaterial {
        id: solid

        objectName: "structure.view.material"
        baseColor: "white"
        metalness: 0
        roughness: scene.roughness
        specularAmount: scene.specularAmount
    }

    Model {
        id: spheresModel

        objectName: "structure.view.spheresModel"
        visible: spheresTable.count > 0
        pickable: true
        instancing: spheresTable
        geometry: SphereGeometry {
            // Built on the spot in the browser: the single-thread build has no thread to build it on, and an
            // asynchronous mesh there never arrives. The desktop keeps the default.
            asynchronous: Qt.platform.os !== "wasm"
            radius: 1
            segments: scene.controller.sphereSegments
            rings: scene.controller.sphereRings
        }
        materials: [solid]
    }
    Model {
        id: cylindersModel

        objectName: "structure.view.cylindersModel"
        visible: cylindersTable.count > 0
        instancing: cylindersTable
        geometry: CylinderGeometry {
            // Built on the spot in the browser: the single-thread build has no thread to build it on, and an
            // asynchronous mesh there never arrives. The desktop keeps the default.
            asynchronous: Qt.platform.os !== "wasm"
            radius: 1
            length: 1
            rings: 1
            segments: scene.controller.cylinderSegments
        }
        materials: [solid]
    }
    Model {
        id: sharedModel

        objectName: "structure.view.shared"
        visible: sharedGeometry.siteCount > 0
        pickable: true
        geometry: SharedSiteGeometry {
            id: sharedGeometry
        }
        materials: [
            PrincipledMaterial {
                baseColor: "white"
                vertexColorsEnabled: true
                cullMode: Material.NoCulling
                metalness: 0
                roughness: scene.roughness
                specularAmount: scene.specularAmount
            }
        ]
    }
    Model {
        objectName: "structure.view.triad.shaftsModel"
        visible: shaftsTable.count > 0
        instancing: shaftsTable
        geometry: CylinderGeometry {
            // Built on the spot in the browser: the single-thread build has no thread to build it on, and an
            // asynchronous mesh there never arrives. The desktop keeps the default.
            asynchronous: Qt.platform.os !== "wasm"
            radius: 1
            length: 1
            rings: 1
            segments: 16
        }
        materials: [solid]
    }
    Model {
        objectName: "structure.view.triad.headsModel"
        visible: headsTable.count > 0
        instancing: headsTable
        geometry: ConeGeometry {
            // Built on the spot in the browser: the single-thread build has no thread to build it on, and an
            // asynchronous mesh there never arrives. The desktop keeps the default.
            asynchronous: Qt.platform.os !== "wasm"
            topRadius: 0
            bottomRadius: 1
            length: 1
            rings: 1
            segments: 16
        }
        materials: [solid]
    }
}
