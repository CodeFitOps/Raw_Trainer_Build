#!/usr/bin/env python3
"""Migra workouts RawTrainer a claves snake_case + MODE canonico.

Preserva descripciones multilinea (block scalars) y el orden de las claves.
Dry-run por defecto: no escribe nada salvo que se pase --out o --apply.

Uso:
  python migrate_to_snake_case.py <dir|fichero> [...] [--out DIR] [--apply]
"""
from __future__ import annotations
import argparse, io
from pathlib import Path
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq

# Claves con espacios/parentesis -> snake_case (el resto se resuelve con .lower())
SPECIAL_KEYS = {
    "eccentric (neg)": "eccentric_neg",
    "isometric (hold)": "isometric_hold",
}
# Sinonimos de MODE -> token canonico en minusculas
MODE_SYNONYMS = {
    "custom": "custom_sets", "custom_set": "custom_sets", "custom_sets": "custom_sets",
    "tabata": "tabata", "emom": "emom", "amrap": "amrap",
    "for_time": "for_time", "fortime": "for_time", "ft": "for_time",
    "afap": "for_time", "chipper": "for_time", "edt": "edt",
}

def canon_key(k):
    kl = str(k).strip().lower()
    return SPECIAL_KEYS.get(kl, kl)

def canon_mode(v):
    if not isinstance(v, str):
        return v, False
    low = v.strip().lower()
    new = MODE_SYNONYMS.get(low, low)
    return new, (new != v)

def transform(node, stats):
    if isinstance(node, dict):
        out = CommentedMap()
        for k, val in node.items():
            nk = canon_key(k)
            if str(nk) != str(k):
                key = f"{k!r} -> {nk!r}"
                stats["keys"][key] = stats["keys"].get(key, 0) + 1
            if nk == "mode":
                nv, changed = canon_mode(val)
                if changed:
                    key = f"{val!r} -> {nv!r}"
                    stats["modes"][key] = stats["modes"].get(key, 0) + 1
                out[nk] = nv
            else:
                out[nk] = transform(val, stats)
        return out
    if isinstance(node, list):
        seq = CommentedSeq()
        for it in node:
            seq.append(transform(it, stats))
        return seq
    return node

def make_yaml():
    y = YAML()
    y.preserve_quotes = True
    y.width = 4096
    y.indent(mapping=2, sequence=4, offset=2)
    return y

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+")
    ap.add_argument("--apply", action="store_true", help="reescribe el propio fichero")
    ap.add_argument("--out", help="directorio de salida (preview)")
    args = ap.parse_args()

    files = []
    for p in args.paths:
        p = Path(p)
        if p.is_dir():
            files += sorted(p.glob("*.yaml")) + sorted(p.glob("*.yml"))
        else:
            files.append(p)

    yaml = make_yaml()
    total = {"keys": {}, "modes": {}}
    n_ok = n_err = n_changed = 0
    for f in files:
        stats = {"keys": {}, "modes": {}}
        try:
            data = yaml.load(f.read_text(encoding="utf-8"))
        except Exception as e:
            print(f"  PARSE-ERROR  {f.name}: {str(e).splitlines()[0][:70]}")
            n_err += 1
            continue
        new = transform(data, stats)
        changed = bool(stats["keys"] or stats["modes"])
        n_ok += 1
        n_changed += 1 if changed else 0
        for kk, vv in stats["keys"].items():
            total["keys"][kk] = total["keys"].get(kk, 0) + vv
        for kk, vv in stats["modes"].items():
            total["modes"][kk] = total["modes"].get(kk, 0) + vv
        print(f"  {'CAMBIA' if changed else 'ok    '}  {f.name}")
        if args.apply or args.out:
            buf = io.StringIO()
            yaml.dump(new, buf)
            text = buf.getvalue()
            if args.out:
                outdir = Path(args.out); outdir.mkdir(parents=True, exist_ok=True)
                (outdir / f.name).write_text(text, encoding="utf-8")
            if args.apply:
                f.write_text(text, encoding="utf-8")
    print(f"\n  Ficheros: {n_ok} ok ({n_changed} con cambios), {n_err} con error de parseo")
    print("\n  Renombrados de clave (agregado):")
    for k, v in sorted(total["keys"].items(), key=lambda x: -x[1]):
        print(f"    {v:>3}x  {k}")
    print("\n  Normalizaciones de MODE (agregado):")
    for k, v in sorted(total["modes"].items(), key=lambda x: -x[1]):
        print(f"    {v:>3}x  {k}")

if __name__ == "__main__":
    main()
