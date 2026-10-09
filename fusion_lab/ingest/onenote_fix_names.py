"""Einmalige Reparatur nach dem Dateinamen-Fehler (bis 08.10.2026).

Alte Namen endeten auf die letzten 8 Zeichen der Seiten-ID -- das ist die
Abschnitts-ID, gleichnamige Seiten eines Abschnitts teilten sich also eine
Datei. Dieses Skript (nur laufen lassen, wenn KEIN Import laeuft):
  * eindeutige Seiten: Dateien (.html/.md/_imgN.*) auf den neuen Namen umbenennen
  * kollidierte Seiten: gemeinsame Dateien loeschen und die Eintraege aus dem
    Manifest nehmen -> der naechste Import laedt sie mit eindeutigem Namen neu

    python -m fusion_lab.ingest.onenote_fix_names
"""

import collections
import sys

from fusion_lab.ingest.common import load_json, safe_name, save_json
from fusion_lab.ingest.onenote import MANIFEST, OUT_DIR, page_stem


def old_stem(pid: str, entry: dict) -> str:
    return safe_name(entry.get("title") or "ohne Titel") + "__" + pid[-8:]


def folder_of(entry: dict):
    return OUT_DIR.joinpath(*[safe_name(p) for p in entry["path"].split("/")])


def files_for(folder, stem):
    # iterdir statt glob: Titel mit [ ] wuerden als Glob-Muster gelesen
    if not folder.exists():
        return []
    return [f for f in folder.iterdir()
            if f.stem == stem or f.name.startswith(stem + "_img")]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    manifest = load_json(MANIFEST, {})
    groups = collections.defaultdict(list)
    for pid, e in manifest.items():
        if "file" not in e:
            groups[(e["path"], old_stem(pid, e))].append(pid)

    renamed = dropped = 0
    for (path, stem), pids in groups.items():
        folder = folder_of(manifest[pids[0]])
        files = files_for(folder, stem)
        if len(pids) > 1:
            for f in files:
                f.unlink()
            for pid in pids:
                del manifest[pid]
            dropped += len(pids)
            continue
        pid = pids[0]
        new = page_stem({"id": pid, "title": manifest[pid].get("title")})
        for f in files:
            f.rename(f.with_name(new + f.name[len(stem):]))
        manifest[pid]["file"] = new
        renamed += 1
    save_json(MANIFEST, manifest)
    print(f"umbenannt: {renamed} Seiten, zum Neuladen markiert: {dropped} Seiten")
    return 0


if __name__ == "__main__":
    sys.exit(main())
