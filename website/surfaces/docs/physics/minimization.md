---
template: physics.html
---

# Minimization and uncertainty

## Independent parameters and Jacobian {#eq-jacobian}

For the weighted residual vector $\mathbf r$ defined in [Rietveld refinement](rietveld.md#eq-weighted-residual), let $J_{ij}=\partial r_i/\partial p_j$. The Jacobian columns correspond to independent free parameters; fixed, symmetry-related and constrained dependent values are not extra columns.

The scientific models and their derivatives share their declared parameter conventions. A parameter that is only stored has no nonzero model derivative merely because a numerical value is present in the file.

## Levenberg–Marquardt step {#eq-lm}

A scaled damped least-squares step has the form

$$(J^{\mathsf T}J+\lambda D)\Delta\mathbf p=-J^{\mathsf T}\mathbf r.$$

$D$ supplies the diagonal scaling/damping convention; $\lambda$ controls damping. The implemented strategy controls the acceptance and damping search, while the scientific objective remains the weighted residual sum.

| Descent selector | Meaning |
| --- | --- |
| `ladder` | Damping-ladder LM search |
| `fast_descent` | Additional in-iteration damping re-search |
| `fast_descent_linear_snap` | Re-search with a full linear-block solve |
| `fast_descent_guarded_linear_snap` | Accept a linear snap only when it improves the objective |
| `multistart_prune` | A two-probe multi-start/pruning strategy using one progress stream |

The project records its descent, positive relative objective tolerance and positive iteration budget. A budget stop is not the same as convergence. Some strategies have restrictions when bounds are declared; inspect the reported diagnostic rather than assuming every combination is supported.

## Covariance and standard uncertainties {#eq-covariance}

At the final state, the current covariance convention is the scaled inverse curvature

$$C=\chi^2_{\rm red}(J^{\mathsf T}J)^+,\qquad u(p_j)=\sqrt{\max(C_{jj},0)},\qquad
\rho_{jk}=C_{jk}/\sqrt{C_{jj}C_{kk}}.$$

The Jacobian here is already weighted. The implementation computes a column-scaled pseudoinverse and transforms back to physical parameter units, using the undamped final curvature. The `+` denotes that numerical pseudoinverse; it is not an inverse of the damped LM step matrix.

The reduced-χ² scaling is an explicit convention. Do not silently substitute an unscaled covariance from another program. A zero-sensitivity direction or numerical degeneracy requires inspecting the associated diagnostics; a zero reported uncertainty does not make an unmeasured parameter exact.

## Constraints and bounds {#constraints-and-bounds}

A constraint relates quantities and reduces independent freedom. Physical admissibility limits, editable optimizer bounds and symmetry restrictions serve different purposes. The application's displayed minimum and maximum are model-admissibility information; they are not a promise of controls for setting optimizer search bounds.

Use [Parameters](../user-guide/parameters.md) for practical interpretation. The fit's observation set and parameter count also determine the [reliability factors](reliability.md).
