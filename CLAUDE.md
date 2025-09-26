# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PyJalLib is a Python library for 3D game character development pipelines, specifically designed for 3ds Max and Unreal Engine 5 workflows. The library provides tools for character asset management, pipeline automation, and Perforce version control integration.

## Development Commands

### Documentation Generation
```bash
# Generate API documentation using pdoc
powershell -ExecutionPolicy Bypass -File generate_docs.ps1
```

### Package Management
```bash
# Install the package in development mode
uv pip install .

# Install development dependencies
uv pip install pdoc
```

### Testing
```bash
# Run individual test files
python tests/p4Test.py
python tests/moduleImportTest.py
python tests/template_processor_test.py
```

Note: This project uses individual test files rather than a unified test runner. Each test file can be run independently.

## Architecture Overview

### Core Package Structure

The library is organized into three main modules under `src/pyjallib/`:

1. **max/** - 3ds Max integration tools
2. **ue5/** - Unreal Engine 5 integration tools
3. **perforceCore/** - Perforce version control core functionality

### Main Modules

#### 3ds Max Integration (`max/`)
- **Skeleton Management**: `skeleton.py`, `bone.py`, `bip.py` - Bone hierarchy and animation systems
- **Character Tools**: `autoClavicle.py`, `twistBone.py`, `volumeBone.py`, `shoulder.py`, etc. - Specialized bone tools
- **Animation**: `anim.py`, `rootMotion.py` - Animation handling and root motion
- **Asset Pipeline**: `fbxHandler.py`, `skin.py`, `morph.py` - Asset import/export and processing
- **UI Components**: `ui/Container.py`, `progress.py` - User interface elements
- **Utilities**: `name.py`, `helper.py`, `align.py`, `select.py`, `link.py` - General utilities

#### Unreal Engine 5 Integration (`ue5/`)
- **Two-tier architecture**: Core modules work without UE5, `inUnreal/` submodule requires UE5 runtime
- **Template System**: `templates/` - Import template definitions for skeletal meshes, animations, and skeletons
- **Template Processing**: `templateProcessor.py` - Processes import templates
- **Asset Importers** (in `inUnreal/`): `skeletalMeshImporter.py`, `animationImporter.py`, `skeletonImporter.py`

#### Perforce Integration
- **Legacy Interface**: `perforce.py` - Main user-facing Perforce class
- **Core System** (`perforceCore/`):
  - `adapter.py` - P4Python wrapper
  - `service.py` - High-level Perforce operations
  - `dtos.py` - Data transfer objects

### Key Design Patterns

#### Service Injection Pattern
Many classes accept service dependencies in constructors (e.g., `Skeleton` class accepts `animService`, `nameService`, etc.), with automatic fallback to default instances if not provided.

#### Conditional Module Loading
The UE5 module uses try/catch imports to gracefully handle missing Unreal Engine dependencies, allowing core functionality to work without UE5 installed.

#### Legacy Compatibility
The Perforce module maintains backward compatibility by exposing the underlying P4 handle while delegating to the new core architecture.

## Important Implementation Details

### 3ds Max Dependency
Most modules in `max/` require `pymxs` (3ds Max Python integration) and will only function within 3ds Max environment.

### UE5 Environment Detection
The `ue5` module includes helper functions `is_ue5_available()` and `get_module_status()` to check runtime environment capabilities.

### Module Reloading
The library includes a `reload_modules()` function for development workflow, particularly useful when iterating on code within 3ds Max.

### Error Handling
Custom exception hierarchy defined in `exceptions.py`:
- `PyJalLibError` - Base exception
- `PerforceError`, `MaxError`, `UE5Error` - Environment-specific errors
- `ValidationError`, `FileOperationError`, `NamingConfigError` - Operation-specific errors

## Development Notes

### Testing Strategy
Tests are organized as individual files rather than using a test framework. Each test file demonstrates usage patterns and can be run independently for development verification.

### Documentation
The project uses `pdoc` for API documentation generation. The PowerShell script `generate_docs.ps1` handles the full documentation build and git workflow.

### Naming and Configuration
The library includes a comprehensive naming system (`naming.py`, `namingConfig.py`, `namePart.py`) for consistent asset naming across the pipeline.