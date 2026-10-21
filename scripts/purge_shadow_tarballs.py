#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import glob
import os
import re
import sys
from pathlib import Path

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent

def clean_dir(d: Path):
    if not d.is_dir():
        return
    removed = 0
    for f in d.glob("*.tgz"):
        # 只要没有跟随版本号 (-X.Y.Z) 的都是影子别名包
        if not re.search(r"-\d+\.\d+", f.name):
            try:
                f.unlink()
                removed += 1
                print(f"  🗑️ Removed shadow tarball: {f.name}")
            except Exception as e:
                print(f"  ⚠️ Failed to remove {f.name}: {e}")
    print(f"✔ Cleaned {removed} shadow tarballs in {d}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dir", default="")
    args = parser.parse_args()
    if args.dir:
        clean_dir(Path(args.dir))
    else:
        clean_dir(ROOT / "public")
        clean_dir(ROOT / "dist")
