# Python Project Technical Specifications

## 1. Development Environment
- **Target OS:** Windows 10/11
- **Shell Environment:** PowerShell (Default)
- **Language:** Python 3.9+ (Must support DCC internal interpreters)
- **Package Manager:** `uv` (Strictly enforced for external libs. Do NOT use `pip` directly.)

## 2. Project Structure
- **`src/`**: Source code root.
- **`tests/`**: Test suite root (mirrors `src` structure).
- **`.ai_context/`**: AI context, manuals, and planning documents.

## 3. Dependency Management
- **Installation:** Use `uv sync` to install dependencies from `pyproject.toml`.
- **Adding Libs:** Use `uv add <package>` for runtime deps, `uv add --dev <package>` for dev deps.
- **Virtual Env:** Always run commands within the environment using `uv run <command>`.

## 4. Testing & Quality
- **Framework:** `pytest`
- **Linting:** `ruff` (check via `uv run ruff check .`)
- **Formatting:** `ruff` (format via `uv run ruff format .`)

## 5. External API Integration (DCC Tools)
- **Target APIs:** `pymxs` (3ds Max), `unreal` (Unreal Engine 5)
