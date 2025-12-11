#!/usr/bin/env python3
import argparse
import sys
import os
from typing import List, Dict, Any

import yaml

REQUIRED_GROUPS: Dict[str, Dict[str, List[str]]] = {
    "deploy_dag": {
        "dev": ["data_science_dev", "platform_engineers_dev"],
        "stage": ["data_science_stage", "platform_approvers_stage"],
        "prod": ["model_publishers_prod"],
    }
}


def load_groups(env: str, base_dir: str = ".") -> Dict[str, Any]:
    yaml_path = os.path.join(base_dir, "ad_groups", f"{env}.yaml")
    if not os.path.exists(yaml_path):
        print(f"[authz] ERROR: AD group config not found: {yaml_path}", file=sys.stderr)
        sys.exit(2)

    with open(yaml_path, "r") as f:
        data = yaml.safe_load(f) or {}

    return data.get("groups") or {}


def user_in_groups(user: str, groups: Dict[str, Any], required: List[str]) -> bool:
    for group_name in required:
        info = groups.get(group_name) or {}
        members = info.get("members") or []
        if user in members:
            return True
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Simple AD-group-like authorization check.")
    parser.add_argument("--env", required=True, help="Target environment: dev/stage/prod")
    parser.add_argument("--user", required=True, help="Triggering user id")
    parser.add_argument("--action", default="deploy_dag", help="Action (default: deploy_dag)")
    parser.add_argument("--base-dir", default=".", help="Platform repo base dir")

    args = parser.parse_args()
    env = args.env.lower()
    user = args.user
    action = args.action

    print(f"[authz] Checking authorization for user='{user}', env='{env}', action='{action}'")

    if action not in REQUIRED_GROUPS:
        print(f"[authz] ERROR: Unknown action '{action}'", file=sys.stderr)
        sys.exit(2)

    env_groups_map = REQUIRED_GROUPS[action]
    if env not in env_groups_map:
        print(f"[authz] ERROR: No group rules for env='{env}', action='{action}'", file=sys.stderr)
        sys.exit(2)

    required_groups = env_groups_map[env]
    groups = load_groups(env, base_dir=args.base_dir)

    if user_in_groups(user, groups, required_groups):
        print(f"[authz] ALLOW: {user} is authorized for {action} in {env}")
        sys.exit(0)

    print(
        f"[authz] DENY: user '{user}' not in groups {required_groups} for env '{env}'",
        file=sys.stderr,
    )
    sys.exit(1)


if __name__ == "__main__":
    main()