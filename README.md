# Platform Services Maintained by Platform

Self-service platform repo that backs a pair of Jenkins jobs for ingesting Airflow DAGs from spoke repos and triggering those DAGs through the Airflow REST API. The scripts in `scripts/` are designed to be called from Jenkins, but they can also be run locally for troubleshooting.

## Repo Layout

| Path | Description |
| --- | --- |
| `ad_groups/` | Mock Active Directory groups per environment that drive authorization. |
| `scripts/authz.py` | Validates that the triggering user belongs to the correct AD-style group for a deploy action. |
| `scripts/validate_project.py` | Ensures a spoke repo’s `project.json` and DAG folder are well formed. |
| `scripts/trigger_airflow_dag.py` | Calls the Airflow REST API to start a DAG run. |
| `services/deploy_dag_airflow/Jenkinsfile` | Jenkins pipeline that clones a spoke repo, validates it, and copies DAGs onto the shared Airflow mount. |
| `services/trigger_dag_airflow/Jenkinsfile` | Jenkins pipeline that triggers a DAG run through Airflow’s API. |

Further Services go into the path services/Job-name/Jenkinsfile

## Prerequisites

- Python 3.9+ available on the Jenkins agent or your workstation.
- Python packages:
  - `PyYAML` (for `authz.py`)
  - `requests` (for `trigger_airflow_dag.py`)
- Access to the shared DAG directory exposed to Airflow (defaults to `/shared/airflow_dags` inside Jenkins).
- Airflow basic-auth credentials stored in Jenkins (`airflow-basic-auth`).

Install the Python dependencies locally:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install requests PyYAML
```

## Configuration

### AD Group Files

Authorization rules live in `ad_groups/<env>.yaml`. Each file defines groups, descriptions, and member user ids. The mapping of required groups per environment is hard-coded inside `scripts/authz.py` under `REQUIRED_GROUPS`. Update both the YAML and that dictionary if you add new environments or actions.

Example (`ad_groups/dev.yaml`):

```yaml
groups:
  data_science_dev:
    description: "DS users allowed to deploy DAGs to dev"
    members:
      - alice
      - bob
```

### Spoke Repo Manifest

Spoke repos must expose a `project.json` at their root. Required keys:

| Key | Purpose |
| --- | --- |
| `project_name` | Used as the folder name under the shared Airflow DAG directory. |
| `team` | Informational owner string surfaced in logs. |
| `dag_path` | Relative path inside the spoke repo containing `.py` DAG files. |
| `allowed_envs` | List of environments (`dev`, `stage`, `prod`) that may deploy this project. |

Sample manifest:

```json
{
  "project_name": "team_a_iris_pipeline",
  "team": "Team A",
  "dag_path": "dags",
  "allowed_envs": ["dev", "stage"]
}
```

The validator checks that `dag_path` exists and contains at least one `.py` file.

## Jenkins Pipelines

### Deploy DAG to Airflow (`services/deploy_dag_airflow/Jenkinsfile`)

Parameters:
- `USER_REPO_URL`: Git URL of the spoke repo (required).
- `USER_REPO_BRANCH`: Branch to checkout (default `main`).
- `ENV`: Target environment (`dev`, `stage`, `prod`).
- `TRIGGERING_USER`: User id that must be present in the correct AD group.

Workflow:
1. Checkout this platform repo (provides scripts/config).
2. Run `scripts/authz.py` to ensure the triggering user is allowed to deploy to the requested env.
3. Clone the spoke repo into `spoke_repo/`.
4. Run `scripts/validate_project.py --env <ENV> --spoke-dir spoke_repo` to ensure `project.json` and DAG folders are valid.
5. Copy the validated `.py` DAG files from the spoke repo into `/shared/airflow_dags/<ENV>/<project_name>/`.

### Trigger Airflow DAG (`services/trigger_dag_airflow/Jenkinsfile`)

Parameters:
- `DAG_ID`: Airflow DAG id to trigger.
- `ENV`: Logical environment label (used for tagging).
- `RUN_ID_PREFIX`: Prefix for the generated `dag_run_id`.
- `DAG_CONF_JSON`: Optional JSON for `dag_run.conf`.

Workflow:
1. Checkout this repo (provides the Python client script).
2. Run `scripts/trigger_airflow_dag.py` with Jenkins-managed Airflow credentials to call `POST /api/v1/dags/<dag_id>/dagRuns`.
3. Surface the HTTP response in the Jenkins logs; fail the build if the API call is not 2xx.

## Python Script Usage

Run these the same way Jenkins does to repro issues locally.

```bash
# Authorization check
python3 scripts/authz.py \
  --env dev \
  --user alice \
  --action deploy_dag \
  --base-dir .

# Validate a spoke repo that was cloned into ./spoke_repo
python3 scripts/validate_project.py \
  --env dev \
  --spoke-dir ./spoke_repo

# Trigger a DAG (set AIRFLOW_USERNAME/PASSWORD env vars first)
export AIRFLOW_USERNAME="user"
export AIRFLOW_PASSWORD="pass"
python3 scripts/trigger_airflow_dag.py \
  --airflow-base-url http://airflow-webserver:8080 \
  --dag-id team_a_dev_iris_pipeline \
  --env dev \
  --run-id-prefix manual_test
```

## Local Workflow Example

1. Clone the spoke repo you want to validate into `spoke_repo/`.
2. Run the auth script with the desired env/user to ensure your user is in the right group.
3. Run the validator to confirm the manifest and DAG directory.
4. Copy DAG files to your local Airflow mount (or rely on Jenkins to do it in CI/CD).
5. Trigger a DAG run locally (pointing at dev/stage Airflow) to verify it registers correctly.

