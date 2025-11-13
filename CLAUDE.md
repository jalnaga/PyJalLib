# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PyJalLib is a Python library for 3D game character development pipelines, bridging **3DS Max**, **Unreal Engine 5**, and **Perforce** version control. The codebase uses service-oriented architecture with dependency injection and graceful handling of optional dependencies (Unreal Engine).

## Development Commands

### Package Management
```powershell
# Install dependencies (uses uv for fast package management)
uv pip install -e .

# Install with Perforce support
uv pip install ".[perforce]"
```

### Documentation
```powershell
# Generate API docs with pdoc
.\generate_docs.ps1

# This script:
# 1. Installs pdoc and project
# 2. Generates docs to docs/ directory
# 3. Commits and pushes to GitHub
```

### Testing
```powershell
# Run specific test file
python tests/test_devStorage_Changelist.py

# Tests are currently manual scripts in tests/ directory
# No pytest framework configured yet
```

### Building and Publishing
```powershell
# Build distribution
uv build

# Version is managed in pyproject.toml (currently 0.1.20)
```

## Architecture Overview

### Module Structure

```
pyjallib/
├── Naming System (namePart.py, naming.py, namingConfig.py)
│   └── Core foundation used by all other modules
├── max/                    # 3DS Max integration (requires pymxs)
│   ├── Service classes (Anim, Name, Bone, Bip, Skeleton, etc.)
│   ├── Helper bone classes (TwistBone, GroinBone, AutoClavicle, etc.)
│   └── ConfigFiles/3DSMaxNamingConfig.json
├── ue5/                    # Unreal Engine 5 integration
│   ├── Core (works without UE5): logger, templateProcessor, templates
│   ├── inUnreal/ (requires UE5): BaseImporter, importers, ImporterSettings
│   └── ConfigFiles/UE5NamingConfig.json
├── perforceCore/          # Internal Perforce implementation
│   ├── adapter.py         # P4Python wrapper with path normalization
│   ├── service.py         # Business logic layer
│   └── dtos.py            # Data transfer objects
└── perforce.py            # Public Perforce facade API
```

### Key Architectural Patterns

#### 1. Naming System (Three-Layer Composition)
- **NamePart**: Atomic name components (Prefix, Suffix, RealName, Index) with semantic types and weights
- **Naming**: Orchestrates NamePart collections, handles parsing/composition/mirroring
- **NamingConfig**: Manages persistence (JSON files), CSV imports, constraint enforcement

The naming system is foundational - both Max and UE5 modules depend on it for consistent asset naming.

#### 2. Perforce (Facade + Core Layering)
- **perforceCore.P4Adapter**: Thin wrapper around P4Python, normalizes paths
- **perforceCore.PerforceService**: Business logic for changelist/file operations
- **perforce.Perforce**: Public facade with backward-compatible API

All file paths are normalized to Windows absolute paths at the adapter level to prevent subtle bugs.

#### 3. Max Services (Dependency Injection)
Services follow a composable hierarchy with lazy defaults:

```python
# Example from Skeleton class
def __init__(self, animService=None, nameService=None, boneService=None, ...):
    self.anim = animService if animService else Anim()
    self.name = nameService if nameService else Name()
    self.bone = boneService if boneService else Bone(nameService=self.name, animService=self.anim)
```

Benefits:
- No global state; independently testable
- Shared state by injecting same service instances
- Services auto-load their naming configs from ConfigFiles/

Common service hierarchy:
- **Bottom tier**: Anim, Name, Helper (standalone utilities)
- **Middle tier**: Bone, Bip (compose lower services)
- **Top tier**: Skeleton, UE5Skeleton (compose multiple services)

#### 4. UE5 Two-Tier Structure
The module gracefully handles missing Unreal Engine:

- **Tier 1 (ue5/)**: Works without UE5 - logger, templateProcessor, templates
- **Tier 2 (ue5/inUnreal/)**: Requires `import unreal` - importers, settings

Check availability: `from pyjallib.ue5 import is_ue5_available`

### Important Implementation Details

1. **NamePart Type System**: PREFIX/SUFFIX types require predefined values; REALNAME/INDEX don't. This is enforced to prevent configuration errors.

2. **Weight-Based Mirroring**: NamePart weights drive intelligent name mirroring (L↔R, Front↔Back) by finding semantically opposite values.

3. **Perforce Auto-Revert**: PerforceService automatically reverts unchanged files on submit (configurable via `in_auto_revert_unchanged`).

4. **Path Normalization**: Always happens once at P4Adapter entry to ensure consistency throughout the stack.

5. **Service Composition**: Max services compose rather than inherit, enabling flexible configuration without deep hierarchies.

6. **Config File Loading**: Services auto-load from `ConfigFiles/` subdirectories. Override by passing `configPath` parameter.

## Working with Max Module

The Max module requires **3DS Max with pymxs**. It provides:
- Skeleton/rig management (Biped, bones, constraints)
- Animation utilities (keyframes, ranges, root motion)
- Naming services integrated with 3DS Max scene
- Helper bone automation (twist bones, volume bones, etc.)
- FBX export handling
- UI components (PySide2-based)

Example service composition:
```python
from pyjallib.max import Skeleton, Name, Anim

# Use default services
skeleton = Skeleton()

# Or inject shared naming
naming = Name(configPath="custom_config.json")
skeleton = Skeleton(nameService=naming)
```

## Working with UE5 Module

Check UE5 availability before importing Unreal-dependent features:
```python
from pyjallib.ue5 import is_ue5_available, get_module_status

if is_ue5_available():
    from pyjallib.ue5.inUnreal import SkeletonImporter, AnimationImporter
else:
    # Use standalone template processing
    from pyjallib.ue5 import TemplateProcessor
```

Template system uses JSON files in `templates/` for import settings.

## Working with Perforce

```python
from pyjallib.perforce import Perforce

p4 = Perforce()
p4.connect("workspace_name")

# Create changelist
cl_info = p4.create_change_list("Description")

# Checkout files
p4.checkout_files_to_change_list(cl_info['id'], ["path/to/file.fbx"])

# Submit
p4.submit_change_list(cl_info['id'])
```

The facade maintains backward compatibility while delegating to perforceCore services internally.

## Exception Handling

Custom exception hierarchy:
```
PyJalLibError
├── PerforceError          # P4 operations
├── ValidationError        # Input validation
├── FileOperationError     # File I/O issues
├── NamingConfigError      # Config loading/parsing
├── MaxError               # 3DS Max operations
└── UE5Error               # Unreal Engine operations
```

Catch specific exceptions for targeted error handling.

## Configuration Files

Config files use JSON format and are located in `*/ConfigFiles/` subdirectories:
- `max/ConfigFiles/3DSMaxNamingConfig.json`: Max naming configuration
- `ue5/ConfigFiles/UE5NamingConfig.json`: UE5 naming configuration

Structure includes:
- `paddingNum`: Number of digits for index padding
- `nameParts`: Array of NamePart definitions with types, predefined values, weights
- Part order determines type assignment (before RealName = PREFIX, after = SUFFIX)

## Code Style Notes

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

## When Adding New Features

1. **New Max service**: Follow dependency injection pattern, accept service instances in `__init__`
2. **New UE5 importer**: Subclass `BaseImporter`, implement required methods
3. **New Perforce workflow**: Extend `PerforceService` in perforceCore, expose via facade
4. **New naming rules**: Add to NamePart predefined values or create custom NamePartType
5. **Tests**: Add manual test scripts to `tests/` directory (no pytest framework yet)
