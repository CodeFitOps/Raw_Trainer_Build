# Managing user libraries (admin / beta ops)

Before coach mode ships, this is how you — as admin — put workout files into a beta
tester's library. It rides on the app's existing per-user data model (Cloudflare
Access → a per-user folder), so there's nothing new to set up and no user-type
model to build yet.

## TL;DR

```bash
# from the repo root, with the same Python you run uvicorn with:
python manage_libraries.py push --to tester@example.com --file ./murph.yaml
python manage_libraries.py ls   --to tester@example.com
python manage_libraries.py users
```

## Does the tester need to have logged in first?

**No.** `push` creates their library folder on the fly if it doesn't exist. Because
the folder name is a deterministic hash of their email, whatever you pre-load is
exactly what they'll find the first time they log in. The only requirement: push to
the **same email they log in with** (case doesn't matter — it's normalized).
Pre-loading a library before a tester's first login is a fine, supported workflow.

This per-user split only exists in **Access mode** (behind Cloudflare Access). If you
run locally with no `CF_ACCESS_*` env there's a single global library and nothing to
target — this tool is for the deployed, Access-gated beta.

## Commands

| Command | What it does |
|---|---|
| `push --to EMAIL --file PATH [--as NAME]` | Validate a workout YAML and add it to that user's library. Invalid YAML is refused and nothing is written. `--as` sets the library filename (default: the source filename). |
| `ls --to EMAIL` | List that user's library (filename + workout name). |
| `users` | Every user library on disk, labeled with the email (for addresses you've used) or a slug guess. |
| `path --to EMAIL` | Print that user's library directory. |

Examples:

```bash
python manage_libraries.py push --to ana@box.com --file ./workouts/fran.yaml
python manage_libraries.py push --to ana@box.com --file ./f.yaml --as fran   # store as fran.yaml
python manage_libraries.py ls   --to ana@box.com
python manage_libraries.py users
```

## How it works

- A user's library is `data/users/<key>/workouts_files/`, where
  `<key> = slug(email) + sha256(email)[:10]` (`data_scope.user_key`).
- `push` scopes to that user (`data_scope.use_root(...)`) and calls the app's own
  `library.import_workout` — the **exact same validated import** a user gets when
  they import a file themselves: validate → copy → register → harvest stages/jobs
  for the reuse panel.
- Emails you use are remembered in `data/known_emails.txt` so `users` can label
  folders with the real address instead of a slug.

## Verify it worked

```bash
python manage_libraries.py push --to you@yourdomain.com --file ./some.yaml
python manage_libraries.py ls   --to you@yourdomain.com
# then log into the app as you@yourdomain.com → the workout is in your library
```

## Manual one-off (no script)

The same thing inline — handy for understanding or a one-off:

```bash
python3 - <<'PY'
from pathlib import Path
from src.infrastructure import data_scope
from src.application import library
with data_scope.use_root(data_scope.user_root("tester@example.com")):
    dest, replaced = library.import_workout(Path("murph.yaml"))
print(("replaced" if replaced else "added"), "->", dest)
PY
```

## Notes

- **Snapshot, not a live link.** A pushed workout is a copied file the tester owns;
  editing your source later doesn't change theirs. Push again to update.
- **Email must match.** Push to the address the tester authenticates with — a typo
  makes a different, empty folder.
- **Deps.** Runs with the app's dependencies (the environment you start `uvicorn`
  with). It reuses `src/`, so run it from the repo root.
