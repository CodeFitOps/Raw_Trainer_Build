def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a workout YAML using Workout.from_dict"
    )
    parser.add_argument(
        "workout_file",
        type=Path,
        help="Path to workout YAML file",
    )
    args = parser.parse_args()

    # Configuramos logging para este script.
    # Si quieres más detalle: export RAWTRAINER_LOG_LEVEL=DEBUG
    configure_logging()

    if yaml is None:
        log.error("pyyaml must be installed to use this script.")
        return 1

    try:
        raw_text = args.workout_file.read_text(encoding="utf-8")
    except Exception as exc:  # noqa: BLE001
        log.error("Cannot read %s: %s", args.workout_file, exc)
        return 1

    try:
        data = yaml.safe_load(raw_text)
    except Exception as exc:  # noqa: BLE001
        log.error("YAML parse error in %s: %s", args.workout_file, exc)
        return 1

    log.info("Loaded YAML from %s", args.workout_file)

    # Aquí entra en juego el dominio:
    try:
        workout = Workout.from_dict(data)
    except WorkoutError as exc:
        log.error("Workout is INVALID according to domain model: %s", exc)
        return 2
    except Exception as exc:  # por si se cuela algo inesperado
        log.exception("Unexpected error while building Workout")
        return 3

    # Si llega aquí, el dominio lo considera válido
    log.info(
        "Workout is VALID according to domain model: name=%r stages=%d",
        workout.name,
        len(workout.stages),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())