"""Finalize script — installs all providers at image build time."""

import argparse
import glob
import os
import pathlib
import shutil
import subprocess

UV: str = shutil.which("uv") or ""
if not UV:
    raise RuntimeError("uv not found in PATH")


def main() -> None:
    """Symlink provider binaries and install all provider packages."""
    parser = argparse.ArgumentParser(description="Install AI-Contained providers into the image")
    parser.parse_args()
    for b in glob.glob("/opt/ai-contained-*/bin/*"):
        p = pathlib.Path(b)
        dest = pathlib.Path(f"/usr/local/bin/{p.name}")
        if p.is_file() and not dest.exists():
            os.symlink(b, dest)

    uv_install = [UV, "pip", "install", "--system", "--python", "/usr/local/bin/python3", "--break-system-packages"]
    for provider in sorted(glob.glob("/opt/ai-contained-*/")):
        subprocess.run([*uv_install, provider], check=True)
