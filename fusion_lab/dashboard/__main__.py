from __future__ import annotations

import argparse
import sys

from fusion_lab.dashboard.build import build
from fusion_lab.dashboard.deploy import deploy


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--local", action="store_true", help="nur bauen, nicht hochladen")
    a = p.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    dist = build()
    print(f"Gebaut: {dist / 'index.html'}")
    if not a.local:
        print(deploy(dist))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
