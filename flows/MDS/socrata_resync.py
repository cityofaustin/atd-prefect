#!/usr/bin/env python

"""
Name: Socrata Resync
Description: Upserts the past 30 days of data into socrata
Schedule: "0 3 * * *"
Labels: atd-data02
"""

import os
import docker
import prefect
from datetime import datetime, timedelta

# Prefect
from prefect import Flow, task
from prefect.storage import GitHub
from prefect.run_configs import UniversalRun
from prefect.engine.state import Failed
from prefect.schedules import Schedule
from prefect.schedules.clocks import CronClock
from prefect.backend import get_key_value

from prefect.utilities.notifications import slack_notifier

# First, we must always define the current environment, and default to staging:
current_environment = os.getenv("PREFECT_CURRENT_ENVIRONMENT", "staging")

# Set up slack fail handler
handler = slack_notifier(only_states=[Failed])

# Notice how test_kv is an object that contains our data as a dictionary:
mds_provider = "wheels"
docker_image = f"atddocker/atd-mds-etl:{current_environment}"
environment_variables = get_key_value(key=f"atd_mds_config_{current_environment}")

# Calculate the dates we need to gather data for
current_time = datetime.now()
socrata_sync_date_start = current_time + timedelta(days=-30)
socrata_sync_date_end = current_time + timedelta(days=1)
socrata_sync_date_format = "%Y-%m-%d"


# Sync the data with socrata
@task(
    name="socrata_sync",
    max_retries=2,
    retry_delay=timedelta(minutes=5),
    state_handlers=[handler]
)
def socrata_sync():
    # Task: socrata_sync
    # Description: Upserts the mast month of data into socrata
    socrata_time_min = socrata_sync_date_start.strftime(socrata_sync_date_format)
    socrata_time_max = socrata_sync_date_end.strftime(socrata_sync_date_format)
    socrata_response = docker.from_env().containers.run(
        image=docker_image,
        working_dir="/app",
        command=f"./provider_full_db_sync_socrata.py  --time-min '{socrata_time_min}' --time-max '{socrata_time_max}'",
        environment=environment_variables,
        volumes=None,
        remove=True,
        detach=False,
        stdout=True
    ).decode("utf-8")

    logger = prefect.context.get("logger")
    logger.info(socrata_response)

    return socrata_response


# Next, we define the flow (equivalent to a DAG).
# Notice we use the label "test" to match this flow to an agent.
with Flow(
    # Postfix the name of the flow with the environment it belongs to
    f"atd_mds_socrata_resync_{current_environment}",
    # Let's configure the agents to download the file from this repo
    storage=GitHub(
        repo="cityofaustin/atd-prefect",
        path="flows/MDS/socrata_resync.py",
        ref=current_environment.replace("staging", "main"),  # The branch name
    ),
    # Run config will always need the current_environment
    # plus whatever labels you need to attach to this flow
    run_config=UniversalRun(
        labels=[current_environment, "atd-data02"]
    ),
    schedule=Schedule(clocks=[CronClock("0 3 * * *")])
) as flow:
    flow.add_task(
        socrata_sync
    )

if __name__ == "__main__":
    flow.run()
