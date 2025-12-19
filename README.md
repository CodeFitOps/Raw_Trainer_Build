📁 Estructura relevante.

```
- internal_tools/schemas/            ← JSON Schemas (workout + jobs)
- internal_tools/examples/           ← Workouts de ejemplo
- data/workouts_files/               ← Workouts importados (v1 menu)
- data/run_logs_v2/                  ← Logs de ejecución v2
- src/application/workout_loader.py  ← Loader v1 + v2
- src/domain_v2/workout_v2.py        ← Modelo dominio v2
- src/ui/cli/main_cli.py             ← CLI principal
- src/ui/cli/preview_v2.py           ← Pretty-print v2
- src/ui/cli/run_v2.py               ← Runner interactivo v2
- src/infrastructure/history_v2.py   ← Logging v2
- src/infrastructure/stats_v2.py     ← Estadísticas v2
```

1) JSON Schema Validation (Standalone Tool).
````
python internal_tools/validate_yaml_from_json_schema.py \
  --schema internal_tools/schemas/workout.schema.json \
  my_workout.yaml
````

2) Loader v1 (legacy domain):

Validación + preview + run usando el modelo actual Workout (v1):
````
python -m src.ui.cli.main_cli validate path/to/workout.yaml
python -m src.ui.cli.main_cli preview path/to/workout.yaml
````

3) Loader v2 (JSON Schema + domain v2)
Obtener dict validado:
````
from src.application.workout_loader import load_workout_v2_from_file, SCHEMA_V2_ROOT
data = load_workout_v2_from_file(path, SCHEMA_V2_ROOT)
````
Obtener modelo tipado (WorkoutV2):
````
from src.application.workout_loader import load_workout_v2_model_from_file
w2 = load_workout_v2_model_from_file(path, SCHEMA_V2_ROOT)
````

4) Preview v2 (pretty print avanzado): 
Valida → normaliza → construye WorkoutV2 → imprime FORMATO NUEVO:
````
python -m src.ui.cli.main_cli preview-v2 internal_tools/examples/all_modesplus2.yaml
````

5) Run v2 (manual runner + logging)

Ejecuta un workout con:
- Pausas por stage/job 
- nometraje por stage/job/workout 
- Notas opcionales por job / stage / workout
- Log automático en data/run_logs_v2/*.json
````
python -m src.ui.cli.main_cli run-v2 internal_tools/examples/all_modesplus2.yaml
````

6) Estadísticas v2 (a partir de los run logs)
Lee todos los .json de data/run_logs_v2/:
````
python -m src.ui.cli.main_cli stats-v2
````
Muestra:
- Número total de sesiones.
- Workouts distintos ejecutados.
- Notas opcionales por job / stage / workout.
- Tiempo total y medio de entrenamiento.
- Breakdown por workout.

7) Import Workflow (menú interactivo v1):

Entrar al menú:
````
python -m src.ui.cli.main_cli
[2] Import Workout
````
Flujo:
1.	Pides ruta o file number
2.  Valida con JSON Schema (v2)
3.	Valida con domain v1
4.	Pretty print
5.	Copia a data/workouts_files/
6.	Actualiza workouts_registry.json
7.	Pregunta si quieres correr el workout (runner v1)


8) Menú Legacy Completo:

````
python -m src.ui.cli.main_cli
[1] Run Workout → runner v1
[2] Import Workout
[3] Exit
````

9) Modos soportados (v2)

Los siguientes MODE se aceptan en YAML:

- CUSTOM
- TABATA
- EMOM
- EMOM
- AMRAP
- AMRAP
- FT
- EDT

                          ┌──────────────────────────────┐
                          │        YAML Workout          │
                          │     (user-created file)      │
                          └───────────────┬──────────────┘
                                          │
                                          ▼
                      ┌───────────────────────────────────────┐
                      │ load_workout_v2_from_file(path)        │
                      │  • YAML → dict                         │
                      │  • Validate top-level schema           │
                      │  • Iterate STAGES/JOBS                 │
                      │  • Validate each job schema            │
                      │  • Normalize MODE synonyms             │
                      └───────────────┬───────────────────────┘
                                      │  dict (valid, normalized)
                                      ▼
                     ┌────────────────────────────────────────────┐
                     │ load_workout_v2_model_from_file(path)      │
                     │  • Calls loader v2                         │
                     │  • dict → WorkoutV2 / StageV2 / JobV2      │
                     │  • Strict domain typing                    │
                     └───────────────┬────────────────────────────┘
                                     │ WorkoutV2 object
                                     ▼
                    ┌────────────────────────────────────────────┐
                    │       preview-v2 (format_workout_v2)       │
                    │  • Pretty-print structured output           │
                    │  • Show job MODE descriptions               │
                    │  • Show exercises, rounds, times            │
                    └────────────────────────────────────────────┘


                                     ▼
                     ┌───────────────────────────────────────────┐
                     │         run-v2 (interactive)               │
                     │  • Press ENTER to start workout            │
                     │  • For each stage:                         │
                     │        - ENTER start / ENTER finish        │
                     │        - Duration tracking                 │
                     │        - Optional note                     │
                     │  • For each job:                           │
                     │        - ENTER start / ENTER finish        │
                     │        - Duration tracking                 │
                     │        - Optional note                     │
                     │  • Final workout note                      │
                     └───────────────┬───────────────────────────┘
                                     │ run_summary dict
                                     ▼
                  ┌─────────────────────────────────────────────────┐
                  │         history_v2.save_run_log(summary)        │
                  │   • Saves JSON to:                              │
                  │        data/run_logs_v2/                        │
                  │   • Filename: workoutname_YYYYMMDD-HHMMSS.json   │
                  └─────────────────────────────────────────────────┘

                                     ▼
               ┌──────────────────────────────────────────────────────┐
               │                   stats-v2                           │
               │  • Reads all JSON logs                               │
               │  • Aggregates stats:                                 │
               │      - Total workouts done                           │
               │      - Per workout stats                             │
               │      - Average / total durations                     │
               │      - Notes count                                   │
               │  • Prints summary report                             │
               └──────────────────────────────────────────────────────┘