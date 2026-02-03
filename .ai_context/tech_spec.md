# Python Project Technical Specifications

## 1. Development Environment
- **Target OS:** Windows 10/11
- **Shell Environment:** PowerShell (Default)
- **Language:** Python 3.10+
- **Package Manager:** `uv` (Strictly enforced for external libs. Do NOT use `pip` directly.)
- **IDE:** Cursor with Pylance (for type checking and code quality)

## 2. Project Structure
- **`src/`**: Source code root.
- **`tests/`**: Test suite root (mirrors `src` structure).
- **`.ai_context/`**: AI context, manuals, and planning documents.

## 3. Dependency Management
- **Installation:** Use `uv sync` to install dependencies from `pyproject.toml`.
- **Adding Libs:** Use `uv add <package>` for runtime deps, `uv add --dev <package>` for dev deps.
- **Virtual Env:** Always run commands within the environment using `uv run <command>`.

## 4. Testing
- **Framework:** `pytest`
- **Execution:** `uv run pytest`

## 5. Documentation
- **Framework:** `mkdocs` with `mkdocstrings`

## 6. Key Dependencies
- **`p4python`**: Perforce integration
- **`pymxs`**: 3ds Max Python API (available only in 3ds Max environment)
- **`unreal`**: Unreal Engine 5 Python API (available only in UE5 environment)
- **`loguru`**: Logging

## 7. Code Style Notes

- Korean comments throughout codebase (documentation target audience)
- Service classes use dependency injection pattern
- Type hints used extensively in perforceCore and newer code
- pymxs (3DS Max API) uses runtime namespace pattern: `from pymxs import runtime as rt`

### Naming Conventions
- **Class names**: PascalCase (e.g., `PerforceService`, `NamePart`, `BoneChain`)
- **Method names**: snake_case (e.g., `create_changelist()`, `get_animation_range()`)
- **Variable names**: camelCase (e.g., `workspaceRoot`, `paddingNum`, `nodeArray`)
- **Method parameters**: inCamelCase with `in` prefix (e.g., `inDescription`, `inWorkspaceName`, `inObj`)

Example:
```python
class PerforceService:
    def create_changelist(self, inDescription: str) -> ChangeListInfo:
        changeSpec = self.adapter.run_change_create()
        changeSpec["Description"] = inDescription
        return self._save_and_fetch(changeSpec)
```