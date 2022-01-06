#!/usr/bin/env python

"""
Name: Lime MDS
Description: The purpose of this flow is to gather data from Lime's
    MDS platform every 15th minute of every hour.
Schedule: "15 * * * *"
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
from prefect.triggers import all_successful

from prefect.utilities.notifications import slack_notifier

# First, we must always define the current environment, and default to staging:
current_environment = os.getenv("PREFECT_CURRENT_ENVIRONMENT", "staging")

# Set up slack fail handler
handler = slack_notifier(only_states=[Failed])

# Notice how test_kv is an object that contains our data as a dictionary:
mds_provider = "lime"
docker_image = f"atddocker/atd-mds-etl:{current_environment}"
environment_variables = get_key_value(key=f"atd_mds_config_{current_environment}")
current_time = datetime.now() + timedelta(days=-1)
time_max = f"{current_time.year}-{current_time.month}-{current_time.day}-{(current_time.hour)}"


# Retrieve the provider's data
@task(
    name="provider_extract",
    max_retries=1,
    retry_delay=timedelta(minutes=5),
    state_handlers=[handler]
)
def provider_extract():
    response = docker.from_env().containers.run(
        image=docker_image,
        working_dir="/app",
        command=f"./provider_extract.py --provider '{mds_provider}' --time-max '{time_max}' --interval 1",
        environment=environment_variables,
        volumes=None,
        remove=True,
        detach=False,
        stdout=True
    ).decode("utf-8")
    logger = prefect.context.get("logger")
    logger.info(response)
    return response


# Sync the data with the database
@task(
    name="provider_sync_db",
    max_retries=1,
    retry_delay=timedelta(minutes=5),
    state_handlers=[handler]
)
def provider_sync_db():
    response = docker.from_env().containers.run(
        image=docker_image,
        working_dir="/app",
        command=f"./provider_sync_db.py --provider '{mds_provider}' --time-max '{time_max}' --interval 1",
        environment=environment_variables,
        volumes=None,
        remove=True,
        detach=False,
        stdout=True
    ).decode("utf-8")

    logger = prefect.context.get("logger")
    logger.info(response)

    return response


# Sync the data with socrata
@task(
    name="provider_sync_socrata",
    max_retries=1,
    retry_delay=timedelta(minutes=5),
    state_handlers=[handler]
)
def provider_sync_socrata():
    response = docker.from_env().containers.run(
        image=docker_image,
        working_dir="/app",
        command=f"./provider_sync_socrata.py --provider '{mds_provider}' --time-max '{time_max}' --interval 1",
        environment=environment_variables,
        volumes=None,
        remove=True,
        detach=False,
        stdout=True
    ).decode("utf-8")

    logger = prefect.context.get("logger")
    logger.info(response)

    return response


# Next, we define the flow (equivalent to a DAG).
# Notice we use the label "test" to match this flow to an agent.
with Flow(
    # Postfix the name of the flow with the environment it belongs to
    f"atd_mds_{mds_provider}_{current_environment}",
    # Let's configure the agents to download the file from this repo
    storage=GitHub(
        repo="cityofaustin/atd-prefect",
        path="flows/MDS/lime.py",
        ref=current_environment.replace("staging", "main"),  # The branch name
    ),
    # Run config will always need the current_environment
    # plus whatever labels you need to attach to this flow
    run_config=UniversalRun(
        labels=[current_environment, "atd-data02"]
    ),
    schedule=Schedule(clocks=[CronClock("15 * * * *")])
) as flow:
    flow.chain(
        provider_extract,
        provider_sync_db,
        provider_sync_socrata
    )

if __name__ == "__main__":
    flow.run()
