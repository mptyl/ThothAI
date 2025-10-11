#!/usr/bin/env python3
"""Synchronize local database dependencies based on config.yml.local."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, Any, List

try:
    import yaml  # type: ignore
    import toml  # type: ignore
except ModuleNotFoundError as exc:  # pragma: no cover
    print(f"Error: missing required module {exc.name}. Install PyYAML and toml first.")
    sys.exit(1)

CONFIG_PATH = Path("config.yml.local")
PYPROJECT_TARGETS = {
    "backend": {
        "path": Path("backend/pyproject.toml.local"),
        "relative_dir": "backend",
    },
    "sql_generator": {
        "path": Path("frontend/sql_generator/pyproject.toml.local"),
        "relative_dir": "frontend/sql_generator",
    },
}
DB_MANAGER_VERSION = "0.7.3"
SUPPORTED_DATABASES = {
    "sqlite": "sqlite",
    "postgresql": "postgresql",
    "mariadb": "mariadb",
    "mysql": "mysql",
    "sqlserver": "sqlserver",
    "informix": "informix",
}
FUTURE_DATABASES = {"oracle"}


def load_config(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(
            f"Configuration file '{path}' not found. Copy config.yml to {path} and update it."
        )
    with path.open() as fh:
        return yaml.safe_load(fh) or {}


def load_pyproject_local(path: Path) -> Dict[str, Any]:
    if path.exists():
        with path.open() as fh:
            return toml.load(fh)
    # Create minimal structure if missing
    return {"project": {"dependencies": []}}


def determine_required_extras(config: Dict[str, Any]) -> List[str]:
    databases = config.get("databases", {}) or {}
    extras = {"sqlite"}  # Always include sqlite

    for key, extra in SUPPORTED_DATABASES.items():
        if databases.get(key, False):
            extras.add(extra)

    unsupported_enabled = [db for db in FUTURE_DATABASES if databases.get(db, False)]
    if unsupported_enabled:
        print(
            "WARN: The following databases are enabled but not yet supported locally: "
            + ", ".join(sorted(unsupported_enabled))
        )

    return sorted(extras)


def update_dependencies(local_data: Dict[str, Any], new_dep: str) -> bool:
    project = local_data.setdefault("project", {})
    deps: List[str] = project.setdefault("dependencies", [])

    filtered_deps = [dep for dep in deps if not dep.startswith("thoth-dbmanager")]
    changed = filtered_deps != deps or new_dep not in filtered_deps

    if new_dep not in filtered_deps:
        filtered_deps.append(new_dep)

    project["dependencies"] = filtered_deps

    return changed


def main() -> int:
    try:
        config = load_config(CONFIG_PATH)
    except FileNotFoundError as exc:
        print(f"Error: {exc}")
        return 1

    extras = determine_required_extras(config)
    dependency_string = f"thoth-dbmanager[{','.join(extras)}]=={DB_MANAGER_VERSION}"

    overall_changed = False
    for target_name, target in PYPROJECT_TARGETS.items():
        local_path: Path = target["path"]
        local_pyproject = load_pyproject_local(local_path)
        changed = update_dependencies(local_pyproject, dependency_string)

        if changed:
            local_path.parent.mkdir(parents=True, exist_ok=True)
            with local_path.open("w") as fh:
                toml.dump(local_pyproject, fh)
            print(
                f"Updated {local_path} with dependency: {dependency_string}"
            )
            print(f"SYNC_{target_name.upper()}=true")
            overall_changed = True
        else:
            print(f"No updates required for {local_path}.")
            print(f"SYNC_{target_name.upper()}=false")

    print(f"SYNC_REQUIRED={'true' if overall_changed else 'false'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
