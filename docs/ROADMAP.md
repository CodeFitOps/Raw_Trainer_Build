# RawTrainer — Roadmap / future features

Ideas parked for later. Each entry is written to be implementable without
re-deriving the design.

---

## Weekly schedule — assign workouts to weekdays, jump to "today"

**Idea.** Map each day of the week to a workout file. A menu entry (a "Week /
Today" item) takes you straight to the workout assigned for the current day —
so you open the app and go, no searching.

**UX**
- New hub section `PLAN` with `(w) Week` (and optionally a `(t) Today`
  shortcut that jumps straight in).
- `(w)` opens a compact 7-day view; each day shows its assigned workout (or
  `rest`), with **today highlighted** (theme role, e.g. `accent`).
- Selecting a day opens the existing per-workout action submenu — reuse
  `menu._workout_actions(path)` (Show / Run / Driven / Delete). No new flow.
- From the week view you can **assign** a day (pick from the library) or
  **clear** it (→ rest day).

**Storage** — a local, editable file `data/schedule.yaml` (same spirit as
`themes.yaml` / `lang/*.yaml`):

```yaml
monday:    Lower_A_Plyos_Sled_Farmers
tuesday:   Upper_A_Planche_HSPU_Press_to_Handstand
wednesday: null        # rest
thursday:  Lower_B_Glute_Knee_Strength
friday:    Upper_B_Front_Lever_Muscle_Up
saturday:  null
sunday:    null
```

Values are workout stems/names resolvable by `library.resolve()`.
`null` / missing key = rest day.

**Application layer** — `src/application/schedule.py` (pure, no UI I/O):
- `load_schedule() -> dict[str, str | None]`
- `save_schedule(data) -> Path`
- `assign(day, workout)` · `clear(day)`
- `resolved_for(day) -> Path | None` (uses `library.resolve`, tolerates a
  renamed/missing target — return a "broken" marker so the UI can warn)
- `today_index() -> int` (`datetime.now().weekday()`, Mon=0) and
  `today() -> Path | None`

**CLI / menu**
- `main_cli.cmd_week()` (render the 7 days) and `cmd_today()` (jump to today's
  workout, or say it's a rest day). Add `week` / `today` subcommands.
- `menu.py`: a `PLAN` section with `(w) Week`; the week view lists days, a
  number picks a day → `_workout_actions`.

**i18n** — new keys in `lang/en.yaml` + `lang/es.yaml`: day names (mon…sun),
`week`, `today`, `rest_day`, `no_workout`, `assign`, `clear`, `broken_ref`.

**Theme** — reuse existing roles: `section`, `lib_num`/`lib_name`, `key`, and
`accent` to mark today. No new tokens.

**Edge cases**
- Assigned file renamed/deleted → mark the day broken, offer to reassign.
- Day with no assignment → show `rest`, offer to assign.
- (Future) allow more than one workout per day (a list) — e.g. AM/PM.

**Touchpoints** — new: `application/schedule.py`, `data/schedule.yaml`,
`tests/test_schedule.py`. Edit: `ui/cli/main_cli.py` (+ parser),
`ui/cli/menu.py`, `lang/en.yaml`, `lang/es.yaml`.
