# 0086. A powder's calculation range is its grid

- **Status:** Accepted
- **Date:** 2026-11-15
- **Implementation:** ✅ Implemented
- **Priority:** Medium
- **Forward constraint (binding on new features):** a powder's calculation range is read from and written to its generated grid in `core/` (`edi::pd_calculation_range`, `edi::set_pd_calculation_range`); no surface keeps its own copy of the bounds.

## Context

A powder without measured data is calculated on a grid declared in its file as `_data_range.<axis>_min`, `_max` and `_step`. The loader builds the grid from these, and crysta's writer recovers them from the grid on save, so the model keeps only the points. The Python interface (`two_theta_min`, `time_of_flight_inc`, `x_max` and the rest) at first remembered the values it was given in a map of its own. A maximum between two grid points, such as 20.5 with minimum 10 and step 1, then read back as 20.5 until the project was saved and opened again, when it read 20.

## Decision

The range is the grid. Its minimum and maximum are the grid's first and last points and its step the shortest decimal that builds the grid again, so a maximum between two points reads back at once as the last point below it, and reads the same after a save, a copy or an edit. Setting one value builds the grid again from it and the other two as they now read. Without a grid the values come from the d-spacing window 0.5 to 10 Å through the instrument, with 1000 points. The rules live in `core/`, and the bindings call them for both beam modes.

## Consequences

Nothing outside the model holds a range, so a copied or reloaded experiment has the same range as the original. A value typed between grid points is not kept: setting a smaller step afterwards starts from the last point, not from the value typed.

## Alternatives considered

Keeping the typed bounds in the model and writing them on save would keep 20.5, but crysta's file and writer know only the grid, and both sides would need a new item to say which bounds were typed.
