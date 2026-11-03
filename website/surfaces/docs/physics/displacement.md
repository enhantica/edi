---
template: physics.html
---

# Atomic displacement parameters

Displacement parameters describe the attenuation of coherent scattering by the distribution of positions around each site's average position. Their conventions and coordinate basis matter.

## Isotropic forms {#eq-isotropic-adp}

$$T_{\rm iso}(s)=\exp(-B_{\rm iso}s^2)=\exp(-8\pi^2U_{\rm iso}s^2),\qquad B_{\rm iso}=8\pi^2U_{\rm iso}.$$

Both Biso and Uiso have units Å². An equal numerical value in the two forms does not represent equal displacement. `adp_type` chooses `Biso` or `Uiso`; `adp_iso` carries the corresponding value.

## Anisotropic forms {#eq-anisotropic-adp}

With fractional reflection indices and reciprocal-cell lengths,

$$T_{\rm aniso}=\exp\left[-2\pi^2\sum_{i,j}U_{ij}h_i h_j a_i^*a_j^*\right]
=\exp\left[-\tfrac14\sum_{i,j}B_{ij}h_i h_j a_i^*a_j^*\right].$$

The `beta` convention absorbs the reciprocal-length and $2\pi^2$ factors:

$$T_{\rm aniso}=\exp[-\mathbf h^{\mathsf T}\boldsymbol\beta\mathbf h].$$

`Bani`, `Uani` and `beta` are distinct supported representations. The six independent symmetric components include cross terms: a full $\sum_{i,j}$ counts $ij$ and $ji$, so an off-diagonal entry must not be added as if it were already doubled. Space-group symmetry can constrain the components.

## Interpretation

Check physical plausibility and positive-definiteness where appropriate. A large displacement can compensate for another model error; its fitted uncertainty does not resolve that ambiguity. Link the value to the [parameter index](parameters.md) and the selected convention before discussing it with the assistant.

## References

1. International Union of Crystallography. [Atomic displacement parameter nomenclature](https://www.iucr.org/who-we-are/commissions/commission-on-crystallographic-nomenclature/published-reports/adp). Definitions and coordinate conventions.
2. International Union of Crystallography. [coreCIF definition of isotropic B](https://www.iucr.org/__data/iucr/cifdic_html/1/cif_core.dic/Iatom_site_B_iso_or_equiv.html).
