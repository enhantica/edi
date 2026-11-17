---
category_glyph: "\uf6cf"
template: gui.html
---

# <span class="ed-reference-icon" aria-hidden="true">&#63183;</span> Polyhedra

<!-- group-tags -->
<p class="ed-group-tags"><a class="ed-tag ed-tag--technique" data-ed-tag="sampleForm" data-ed-token="powder" href="../../user-guide/glossary/#powder-diffraction" title="Powder diffraction">pd</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="sampleForm" data-ed-token="single crystal" href="../../user-guide/glossary/#single-crystal-diffraction" title="Single-crystal diffraction">sc</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="beamMode" data-ed-token="constant wavelength" href="../../user-guide/glossary/#constant-wavelength" title="Constant wavelength">cwl</a> <a class="ed-tag ed-tag--technique" data-ed-tag="beamMode" data-ed-token="time-of-flight" href="../../user-guide/glossary/#time-of-flight" title="Time of flight">tof</a> <a class="ed-tag ed-tag--technique" data-ed-tag="probe" data-ed-token="neutron" href="../../user-guide/glossary/#neutron-diffraction" title="Neutron diffraction">neut</a> <a class="ed-tag ed-tag--neutral" data-ed-tag="probe" data-ed-token="x-ray" href="../../user-guide/glossary/#x-ray-diffraction" title="X-ray diffraction">xray</a></p>
<!-- /group-tags -->

## Define the polyhedra

The **Polyhedra** button in the structure view's toolbar shows or hides the coordination polyhedra. On **Structure → Extra**, expand **Polyhedra** to say how they are built:

- **Centre atoms** and **Corner atoms** take element symbols, such as `Co, Si` and `O`. Left empty, the cations are the centres and the anions (N, O, F, S, Cl, Se, Br, Te, I) the corners.
- **Max distance** is the longest centre-to-corner distance in Å. At 0, a corner belongs to a centre when the [bond settings](bonds.md) bond it to that centre.
- **Colour** draws each polyhedron in its centre atom's colour or in grey, **Opacity** runs from 0 (clear) to 1 (solid), and **Extent** draws the polyhedra inside the cell or each one whole for every centre in the cell.

A polyhedron is drawn round each centre atom with at least four corner atoms near it, as the convex shape through those corners. These settings change the picture only, not the crystallographic model, and they last for the session.
