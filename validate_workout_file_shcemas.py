from pathlib import Path
from src.application.workout_loader import (
    load_workout_v2_model_from_file,
    WorkoutLoadError,
)

schema_root = Path("internal_tools/schemas")
workout_file = Path("internal_tools/examples/all_modesplus2.yaml")

try:
    w2 = load_workout_v2_model_from_file(workout_file, schema_root)
    print("OK ✅")
    print("Name:", w2.name)
    print("Stages:", len(w2.stages))
    for si, stage in enumerate(w2.stages, start=1):
        print(f"  Stage {si}: {stage.name} ({len(stage.jobs)} jobs)")
except WorkoutLoadError as exc:
    print("❌ Workout INVALID according to v2 pipeline")
    print("   Error:", exc)