#!/usr/bin/env python3
import argparse
import json
import os
import sys
from typing import Any, Dict


def load_project_manifest(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        print(f"[project] ERROR: project.json not found at {path}", file=sys.stderr)
        sys.exit(2)

    with open(path, "r") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError as e:
            print(f"[project] ERROR: invalid JSON in project.json: {e}", file=sys.stderr)
            sys.exit(2)

    return data


def validate_project(manifest: Dict[str, Any], env: str, spoke_dir: str) -> None:
    required_fields = ["project_name", "team", "dag_path", "allowed_envs"]
    for field in required_fields:
        if field not in manifest:
            print(f"[project] ERROR: missing required field '{field}'", file=sys.stderr)
            sys.exit(2)

    project_name = manifest["project_name"]
    team = manifest["team"]
    dag_path = manifest["dag_path"]
    allowed_envs = manifest["allowed_envs"]

    print(f"[project] project_name = {project_name}")
    print(f"[project] team         = {team}")
    print(f"[project] dag_path     = {dag_path}")
    print(f"[project] allowed_envs = {allowed_envs}")

    if env not in allowed_envs:
        print(
            f"[project] ERROR: env '{env}' not allowed for project '{project_name}'. "
            f"Allowed envs: {allowed_envs}",
            file=sys.stderr,
        )
        sys.exit(1)

    abs_dag_dir = os.path.join(spoke_dir, dag_path)
    if not os.path.isdir(abs_dag_dir):
        print(f"[project] ERROR: dag_path directory does not exist: {abs_dag_dir}", file=sys.stderr)
        sys.exit(2)

    py_files = [f for f in os.listdir(abs_dag_dir) if f.endswith(".py")]
    if not py_files:
        print(f"[project] ERROR: no .py DAG files found under {abs_dag_dir}", file=sys.stderr)
        sys.exit(2)

    print(f"[project] Found DAG files: {py_files}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate spoke repo project.json and DAG structure.")
    parser.add_argument("--env", required=True, help="Target environment (dev/stage/prod)")
    parser.add_argument("--spoke-dir", required=True, help="Path where spoke repo is cloned")

    args = parser.parse_args()
    env = args.env.lower()

    manifest_path = os.path.join(args.spoke_dir, "project.json")
    manifest = load_project_manifest(manifest_path)
    validate_project(manifest, env, args.spoke_dir)


if __name__ == "__main__":
    main()