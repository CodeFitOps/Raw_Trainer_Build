# Internal Tools – RawTrainer

This folder contains developer-only tools used to design, infer, validate, and
maintain the JSON Schemas that describe RawTrainer workout files.

These tools are **not part of the main application runtime**. They exist to:

- Infer JSON Schemas from example YAML files.
- Manually tune those schemas to match the Python domain rules.
- Validate YAML workouts against schemas.
- Generate reusable skeleton YAML templates.

---

## ⚠️ Source of Truth

The authoritative validation logic lives in the **Python domain layer**:

- `Exercise.from_dict`
- `Job.from_dict_custom_sets`
- `Stage.from_dict`
- `Workout.from_dict`

JSON Schemas are *helpers* for tooling, CI and editor validation.
They must always stay aligned with these Python rules.

---

## 📁 Directory Structure

Suggested structure under `internal_tools/`:

```text
internal_tools/
  README.md

  schemas/
    workout.schema.json
    job.custom_sets.schema.json
    # future schemas: job.emom.schema.json, job.amrap.schema.json, ...

  examples/
    job_custom_sets_example.yaml
    job_custom_sets_full.yaml
    workout_custom_sets_example.yaml
    # and future examples for new MODES

  infer_schema_from_yaml.py
  validate_yaml_from_json_schema.py
  create_workout_skeleton.py
```

- `schemas/` → Final JSON Schemas (contracts for YAML structure)
- `examples/` → YAML examples used to infer and test schemas
- Scripts → Tools for inference, validation, and skeleton generation

---

# 🧪 Workflow: Designing or Updating a Job MODE

Use this workflow whenever you add or modify a job mode
(e.g. `custom_sets`, `emom`, `amrap`, etc.)

---

## 1️⃣ Create YAML Examples

Place example files under:

```text
internal_tools/examples/
```

Provide at least:
- A **minimal valid** YAML
- A **full** YAML covering all optional fields

Examples:

- `job_custom_sets_example.yaml`
- `job_custom_sets_full.yaml`
- `workout_custom_sets_example.yaml`

These represent the intended shape of the data for that MODE.

---

## 2️⃣ Infer a Draft JSON Schema

Use the inference script to bootstrap a JSON Schema:

```bash
python internal_tools/infer_schema_from_yaml.py \
  internal_tools/examples/job_custom_sets_example.yaml \
  internal_tools/examples/job_custom_sets_full.yaml \
  --output internal_tools/schemas/job.custom_sets.schema.json
```

This produces a **draft** schema based on the examples.

You can do the same for the top-level workout structure:

```bash
python internal_tools/infer_schema_from_yaml.py \
  internal_tools/examples/workout_custom_sets_example.yaml \
  --output internal_tools/schemas/workout.schema.json
```

---

## 3️⃣ Tune the JSON Schema Manually

Open the generated schema and adjust it so it matches the Python domain rules
in `workout_model.py`.

Typical adjustments:

- Add `"required"` fields
- Set strict `"type"` values
- Add `"enum"` for fields like `MODE`
- Add constraints such as `"minimum": 1` for integer fields
- Add `"anyOf"` or `"oneOf"` for rules such as:
  - Exercise must define **either** `reps` **or** `work_time_in_seconds`

After tuning, the schema becomes a formal contract for editors and CI.

---

## 4️⃣ Validate YAML Files Against the JSON Schema

Use the validation script:

```bash
python internal_tools/validate_yaml_from_json_schema.py \
  --schema internal_tools/schemas/job.custom_sets.schema.json \
  internal_tools/examples/job_custom_sets_example.yaml
```

If the file is valid:

```text
OK: job_custom_sets_example.yaml is valid against job.custom_sets.schema.json
```

If invalid:

```text
INVALID: job_custom_sets_example.yaml does not match job.custom_sets.schema.json
  - At STAGES.0.JOBS.1.EXERCISES.0: 'reps' is a required property
```

Exit codes:
- `0` → valid
- `2` → invalid
- `1` → error reading/parsing schema or YAML

Use this script in:

- Manual CLI checks
- CI pipelines
- Pre-commit hooks
- Batch validation for a folder of workouts

---

## 5️⃣ Keep Schemas and Domain in Sync

Whenever you modify domain rules in `workout_model.py`:

- change required/optional fields,
- change types,
- add/remove constraints,

you **must update** the corresponding JSON Schema under `internal_tools/schemas/`.

The **domain is authoritative**, the schema is its mirror.

---

# 🛠 Scripts Overview

---

## `infer_schema_from_yaml.py`

**Purpose:** bootstrap a JSON Schema from one or more YAML examples.

Usage:

```bash
python internal_tools/infer_schema_from_yaml.py \
  internal_tools/examples/job_custom_sets_example.yaml \
  internal_tools/examples/job_custom_sets_full.yaml \
  --output internal_tools/schemas/job.custom_sets.schema.json
```

Good for:
- Quickly creating a starting schema for a new MODE.
- Regenerating base schemas when examples evolve.

---

## `validate_yaml_from_json_schema.py`

**Purpose:** validate a YAML file against a JSON Schema using `jsonschema`.

Usage:

```bash
python internal_tools/validate_yaml_from_json_schema.py \
  --schema internal_tools/schemas/workout.schema.json \
  path/to/workout.yaml
```

Behaves as:

- Exit `0` if the file is valid.
- Exit `2` if the file is invalid (with detailed error messages).
- Exit `1` if there is a problem reading or parsing schema/YAML.

---

## `create_workout_skeleton.py`

**Purpose:** generate a minimal workout YAML skeleton you can edit manually.

Usage:

```bash
python internal_tools/create_workout_skeleton.py \
  --name "My Workout" \
  --description "Strength + conditioning" \
  --output new_workout.yaml
```

Example output:

```yaml
NAME: "My Workout"
description: "Strength + conditioning"
STAGES: []
```

You then fill in `STAGES`, `JOBS`, and `EXERCISES` according to the schemas and domain rules.

---

## 📂 Examples Directory

`internal_tools/examples/` contains YAML examples that serve as:

- Schema inference sources.
- Validation test cases.
- Living documentation of the expected structure.

Typical files:

```text
job_custom_sets_example.yaml
job_custom_sets_full.yaml
workout_custom_sets_example.yaml
```

Later you might add:

```text
job_emom_example.yaml
job_amrap_example.yaml
...
```

---

## ✅ Final Notes

- The Python domain (`Workout.from_dict` and friends) is the final judge.
- JSON Schemas and these tools improve:
  - Developer experience,
  - Editor validation,
  - CI robustness,
  - Overall safety of workout definitions.

Use this `internal_tools` folder as your lab for experimenting with and hardening the workout file format, while keeping everything aligned with the core domain model.
