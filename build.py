# (c) Copyright Riverlane 2025-2026. All rights reserved.
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path
from typing import Any

from decouple import config
from setuptools import build_meta as _backend


def __getattr__(name: str) -> Any:
    """Forward all unoverridden PEP 517 hooks to setuptools."""
    return getattr(_backend, name)


JS_SRC_DIR = Path("src/deltakit_visualise/.js")

NPM_PKG_NAME = "deltakit-visualise"


def download_npm_pkg(version: str) -> None:
    """Downloads NPM package into the source tree for bundling into the wheel."""
    # check if npm is installed
    if shutil.which("npm") is None:
        msg = "'npm' executable not found, please ensure it is installed"
        raise FileNotFoundError(msg)

    # ensure JS src dir exists or create one
    JS_SRC_DIR.mkdir(parents=True, exist_ok=True)

    # download package. It is published publicly, so no registry auth is needed.
    pkg_name = NPM_PKG_NAME
    npm_registry_url: str = config(
        "NPM_REGISTRY_URL", default="https://registry.npmjs.org/"
    )
    # 'npm pack' fetches only this package's own tarball. 'npm install' would also
    # materialise its full dependency tree (~230MB) here, and all of it would be
    # swept into the wheel -- the UMD build already inlines those dependencies.
    command = ["npm", "pack", f"{pkg_name}@{version}", f"--registry={npm_registry_url}"]
    print(f"Downloading {pkg_name}@{version} from {npm_registry_url}", file=sys.stderr)
    try:
        subprocess.run(
            command,
            check=True,
            cwd=f"{JS_SRC_DIR.absolute()}",
            stdout=subprocess.DEVNULL,
        )
        print(f"Successfully downloaded {pkg_name}@{version}", file=sys.stderr)
    except subprocess.CalledProcessError as e:
        msg = (
            f"Failed to download {pkg_name}@{version} from {npm_registry_url}. "
            f"npm exited with code {e.returncode}. "
            f"Check that: 1) the package version exists, "
            f"2) network access is available."
        )
        raise RuntimeError(msg) from e

    # Unpack dist/ from the tarball. Selecting members explicitly (rather than a bare
    # extractall) stops a renamed entry from writing outside JS_SRC_DIR.
    for tarball in JS_SRC_DIR.glob("*.tgz"):
        with tarfile.open(tarball) as tar:
            members = [
                m for m in tar.getmembers() if m.name.startswith("package/dist/")
            ]
            for member in members:
                member.name = member.name.removeprefix("package/")
            tar.extractall(JS_SRC_DIR, members=members)
        tarball.unlink()

    if not (JS_SRC_DIR / "dist" / "deltakit-visualise.umd.js").exists():
        msg = f"No dist/ assets found in the {pkg_name}@{version} tarball"
        raise RuntimeError(msg)


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    """Build the wheel with JavaScript assets bundled in."""
    # clean up and recreate the .js source directory
    if JS_SRC_DIR.exists():
        shutil.rmtree(JS_SRC_DIR)

    npm_version: str = config("DELTAKIT_VIS_VERSION", default="latest")
    print(
        f"Building deltakit-visualise wheel with {NPM_PKG_NAME}@{npm_version}",
        file=sys.stderr,
    )
    download_npm_pkg(npm_version)
    print("Wheel build completed successfully", file=sys.stderr)
    return _backend.build_wheel(wheel_directory, config_settings, metadata_directory)
