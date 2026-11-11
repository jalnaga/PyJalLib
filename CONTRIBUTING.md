# Contributing to pyjallib

Thank you for your interest in pyjallib. This document explains how to set up a
development environment, run the tests, generate the API documentation, and send
a pull request.

## Development environment

- Python 3.10 (the version in `.python-version`) and [uv](https://docs.astral.sh/uv/).
- Development and testing are done on Windows. The bundled native module
  (`pyjallib.native.alpha_wrap_native`) is built for Windows x64 + CPython 3.10 only.
- 3ds Max and Unreal Editor are not required for the tests in this repository.

```powershell
git clone https://github.com/jalnaga/PyJalLib.git
cd PyJalLib
uv sync
```

`uv sync` creates `.venv` and installs the package in editable mode together with
the development dependencies (pytest, ruff, PySide2). Use `uv add` / `uv run`
rather than calling `pip` directly.

## Running the tests

```powershell
uv run python -m pytest -q
```

The tests run in a plain console Python. Modules that only exist inside 3ds Max
(`pymxs`) or Unreal Editor (`unreal`) are replaced with mocks by the `conftest.py`
files, so the tests cover the logic that does not need a running host
application. If your change affects behaviour inside 3ds Max or Unreal Editor,
please describe in the pull request how you checked it there (application
version, steps, and result).

Lint the files you changed before you send them:

```powershell
uv run ruff check <changed files>
```

`uv run ruff check .` still reports findings in parts of the existing code, so
the goal is that your change does not add new ones.

## Code style

- Classes use `PascalCase`, functions and methods use `snake_case`, variables use
  `camelCase`, and parameters use `camelCase` with an `in` prefix (`inNode`,
  `inFilePath`).
- Type hints are required.
- Comments and docstrings are written in Korean, in Google docstring style.
- Use `pyjallib.Logger` for logging instead of `print()`.
- Library code must keep working inside the Python that ships with 3ds Max and
  Unreal Editor, where extra packages cannot be installed. Do not add third-party
  runtime dependencies without discussing it in an issue first.
- `native/alphaWrap` is vendored third-party code pinned to specific upstream
  commits (see `native/alphaWrap/VENDORED.md`). Please do not edit it in place.

## Generating the API documentation

The API documentation published at <https://jalnaga.github.io/PyJalLib/> is
generated with [pdoc](https://pdoc.dev/) into the `docs/` directory.

```powershell
.\generate_docs.ps1
```

The script only generates files. It does not commit or push anything. pdoc is
fetched for that single run and is not added to the project dependencies. To
write the output somewhere else:

```powershell
.\generate_docs.ps1 -OutputDirectory C:\temp\pyjallib-docs
```

Without PowerShell you can run the generator directly:

```
uv run --with pdoc python docs_support/build_docs.py --output docs
```

You do not need to include regenerated `docs/` files in a pull request.

## Pull requests

1. Open an issue first for larger changes so the approach can be agreed on.
2. Keep each pull request focused on one change, and add or update tests for it.
3. Make sure `uv run python -m pytest -q` passes and ruff reports no new findings
   for the files you changed.
4. Describe what changed and why, and how you verified it.

Accepted changes are integrated by the maintainer. A change may be published as
part of a later update commit instead of a direct merge, in which case the pull
request is closed with a reference to the commit that contains it.

## License

pyjallib is released under the MIT License (see `LICENSE`). By contributing you
agree that your contribution is licensed under the same terms.
