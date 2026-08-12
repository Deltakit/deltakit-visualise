# Building deltakit-visualise

## Overview

The `deltakit-visualise` package includes JavaScript assets that are built into the wheel during the package build process. This ensures users don't need to have Node.js or npm installed at runtime.

## Requirements for Building

To build the wheel with the JavaScript assets, you need:

1. **Python 3.10+** - For building the package
2. **Node.js and npm** - For building the JavaScript assets
   - Download from: https://nodejs.org/
   - Check installation: `node --version` and `npm --version`
3. **uv** - The package manager (or pip/setuptools)

## Building the Wheel

### Using uv (Recommended)

```bash
# From the deltakit-visualise directory
cd deltakit-visualise

# Build the wheel
uv build --wheel
```

The built wheel will be in the `dist/` directory.

### Using pip

```bash
pip wheel . --no-deps -w dist/
```

## Environment Variables

The frontend package is published publicly on npm, so no registry authentication is
needed. Both variables are optional:

```bash
# Optional: Set the npm registry URL (default: https://registry.npmjs.org/)
export NPM_REGISTRY_URL=https://registry.npmjs.org/

# Optional: Set the deltakit-visualise npm version (defaults to "latest" if not set)
export DELTAKIT_VIS_VERSION=0.6.0

# Then build
uv build --wheel
```

## What Happens During Build

1. The custom build backend (`build.py`) is invoked
2. npm runs `npm pack deltakit-visualise` to download the package tarball
3. The tarball's `dist/` assets are extracted to `src/deltakit_visualise/.js/dist/`
4. The wheel is built with these assets included

`npm pack` is used deliberately in place of `npm install`: the UMD bundle already
inlines its dependencies, so installing the dependency tree would add ~230MB of
unused `node_modules` to the wheel and push it past the package index upload limit.

## Troubleshooting

### "npm executable not found"
Install Node.js from https://nodejs.org/

### "NPM package not found"
- Check that you have network access
- Ensure `DELTAKIT_VIS_VERSION` matches a version published at
  https://www.npmjs.com/package/deltakit-visualise

### ".gitignore prevents committing .js/"
The `.js/` directory is build output and should not be committed. It's generated fresh with each build.

## CI Integration Testing

The pull request CI workflow includes an integration test job that validates fresh wheel installs:

1. **Wheel Build**: The `build-wheels` job downloads the latest `deltakit-visualise@latest` npm package during wheel build.
   - No registry credentials are required: the package is public on npmjs.com

2. **Fresh Install Integration Test**: The `integration-visualise` job:
   - Creates a fresh Python 3.13 environment
   - Installs the built wheel (no additional npm install)
   - Runs an integration test via `pytest` to verify the compiler visualisation path executes without error
   - Runs only on new/updated PRs

### CI Troubleshooting

#### Integration job fails to build wheel
- Check that the CI runner has network access to `registry.npmjs.org`
- Verify `DELTAKIT_VIS_VERSION` (if pinned) matches a published version

#### Integration test fails in fresh environment
- Run the integration test locally: `pytest deltakit-visualise/tests/test_latest_install.py -v`
- Running this test directly does not download the latest package from a registry
- It uses whichever `deltakit-visualise` is already installed in your current Python environment
- This test only exercises `VisualiseCompiler.visualise(...)` and does not load `deltakit-visualise.umd.js`
- This test runs on the installed package, so ensure your wheel build/install succeeds first
- If the test passes locally but fails in CI, check for environment-specific issues (file paths, permissions)

#### When is the latest frontend actually validated?
- The latest `deltakit-visualise` npm frontend is fetched during wheel build (`DELTAKIT_VIS_VERSION` defaults to `latest`)
- In this workflow, that happens in CI (`build-wheels`), and `integration-visualise` then tests that built wheel in a clean environment
- So this integration test checks against the latest frontend when run via the CI wheel-build/install path, not when run directly in a local dev environment

#### Validate against the latest published package (not local dev install)
To verify behaviour against the latest published release, run the test in a clean virtual environment and install from the package index first:

```bash
uv venv --python 3.13 .venv-latest
uv pip install --python .venv-latest --upgrade pip
uv pip install --python .venv-latest "deltakit-visualise"
uv pip install --python .venv-latest pytest
.venv-latest/bin/pytest deltakit-visualise/tests/test_latest_install.py -v
```

This ensures the test uses the published package instead of any local editable or workspace install.

## Runtime

Once the package is installed, no npm or Node.js is required. The JavaScript assets are included in the wheel.
