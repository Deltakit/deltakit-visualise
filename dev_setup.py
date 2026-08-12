# (c) Copyright Riverlane 2020-2026.
"""Dev-only script to download the JS assets into src/deltakit_visualise/.js/.

Usage:
    uv run dev_setup.py

Environment variables (same as the build backend):
    NPM_REGISTRY_URL     - npm registry URL (default: https://registry.npmjs.org/)
    DELTAKIT_VIS_VERSION - package version to install (default: latest)
"""

import shutil

from decouple import config

from build import JS_SRC_DIR, NPM_PKG_NAME, download_npm_pkg


def main() -> None:
    print(f"Setting up JS assets in {JS_SRC_DIR.absolute()} ...")

    # Clean previous install so we always get a fresh copy.
    if JS_SRC_DIR.exists():
        shutil.rmtree(JS_SRC_DIR)

    JS_SRC_DIR.mkdir(parents=True, exist_ok=True)

    npm_version: str = config("DELTAKIT_VIS_VERSION", default="latest")
    print(f"Downloading {NPM_PKG_NAME}@{npm_version} ...")
    download_npm_pkg(npm_version)

    print("Done. JS assets installed successfully.")


if __name__ == "__main__":
    main()
