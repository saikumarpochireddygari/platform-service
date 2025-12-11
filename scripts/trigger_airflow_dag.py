#!/usr/bin/env python3
import argparse
import json
import os
import sys
from datetime import datetime

import requests


def parse_args():
    parser = argparse.ArgumentParser(description="Trigger Airflow DAG via REST API")

    parser.add_argument(
        "--airflow-base-url",
        default=os.getenv("AIRFLOW_BASE_URL", "http://airflow-webserver:8080"),
        help="Base URL for Airflow webserver (default: env AIRFLOW_BASE_URL or http://airflow-webserver:8080)",
    )
    parser.add_argument(
        "--dag-id",
        required=True,
        help="Airflow DAG ID to trigger",
    )
    parser.add_argument(
        "--env",
        default="dev",
        help="Logical environment label (dev/stage/prod) just for tagging/conf",
    )
    parser.add_argument(
        "--run-id-prefix",
        default="jenkins_manual",
        help="Prefix for dag_run_id (timestamp is appended)",
    )
    parser.add_argument(
        "--conf-json",
        default=None,
        help="JSON string to use as dag_run.conf (if omitted, uses a default)",
    )

    return parser.parse_args()


def build_conf(env: str, conf_json: str | None) -> dict:
    if conf_json:
        try:
            return json.loads(conf_json)
        except json.JSONDecodeError as e:
            print(f"[ERROR] Invalid JSON in --conf-json: {e}", file=sys.stderr)
            sys.exit(1)

    # Default conf if none provided
    return {
        "triggered_by": "jenkins",
        "env": env,
        "note": "self-service trigger",
    }


def main():
    args = parse_args()

    airflow_base = args.airflow_base_url.rstrip("/")
    dag_id = args.dag_id

    airflow_user = os.getenv("AIRFLOW_USERNAME")
    airflow_pass = os.getenv("AIRFLOW_PASSWORD")
    if not airflow_user or not airflow_pass:
        print(
            "[ERROR] AIRFLOW_USERNAME and AIRFLOW_PASSWORD must be set "
            "(e.g. via Jenkins credentials or environment).",
            file=sys.stderr,
        )
        sys.exit(1)

    run_id = f"{args.run_id_prefix}__{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}"
    conf = build_conf(args.env, args.conf_json)

    payload = {
        "dag_run_id": run_id,
        "conf": conf,
    }

    url = f"{airflow_base}/api/v1/dags/{dag_id}/dagRuns"

    print(f"[INFO] Triggering DAG '{dag_id}' at {url}")
    print(f"[INFO] dag_run_id = {run_id}")
    print(f"[INFO] payload = {json.dumps(payload, indent=2)}")

    try:
        resp = requests.post(
            url,
            auth=(airflow_user, airflow_pass),
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=30,
        )
    except Exception as e:
        print(f"[ERROR] Error calling Airflow API: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"[INFO] HTTP {resp.status_code}")
    try:
        print("[INFO] Response JSON:")
        print(json.dumps(resp.json(), indent=2))
    except Exception:
        print("[INFO] Raw response text:")
        print(resp.text)

    if not (200 <= resp.status_code < 300):
        print("[ERROR] Failed to trigger DAG run", file=sys.stderr)
        sys.exit(1)

    print("[INFO] DAG run triggered successfully.")


if __name__ == "__main__":
    main()