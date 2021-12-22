#!/usr/bin/env python

"""
Name: Process unfinished tasks
Description: The purpose of this flow is to process all stages
    for all active MDS providers. This is basically a catch-all
    process for any failed or missing attempts in the past.

Schedule: "0 2 * * *"
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
docker_image = f"atddocker/atd-mds-etl:{current_environment}"
environment_variables = get_key_value(key=f"atd_mds_config_{current_environment}")

# Current Time
current_time = datetime.now()
current_time_min = current_time + timedelta(days=-90)
current_time_max = current_time + timedelta(days=-1, hours=-8)
time_min = f"{current_time_min.year}-{current_time_min.month}-{current_time_min.day}-01"
time_max = f"{current_time_max.year}-{current_time_max.month}-{current_time_max.day}-{current_time_max.hour}"


# Reprocess unfinished tasks for lime
@task(
    name="process_unfinished_lime",
    max_retries=2,
    retry_delay=timedelta(minutes=5),
    state_handlers=[handler]
)
def process_unfinished_lime():
    response = docker.from_env().containers.run(
        image=docker_image,
        working_dir="/app",
        command=f"./provider_runtool.py --provider 'lime' --time-min '{time_min}' --time-max '{time_max}' --incomplete-only --no-logs",
        environment=environment_variables,
        volumes=None,
        remove=True,
        detach=False,
        stdout=True
    ).decode("utf-8")
    logger = prefect.context.get("logger")
    logger.info(response)
    return response


# Reprocess unfinished tasks for bird
@task(
    name="process_unfinished_bird",
    max_retries=2,
    retry_delay=timedelta(minutes=5),
    state_handlers=[handler]
)
def process_unfinished_bird():
    response = docker.from_env().containers.run(
        image=docker_image,
        working_dir="/app",
        command=f"./provider_runtool.py --provider 'bird' --time-min '{time_min}' --time-max '{time_max}' --incomplete-only --no-logs",
        environment=environment_variables,
        volumes=None,
        remove=True,
        detach=False,
        stdout=True
    ).decode("utf-8")
    logger = prefect.context.get("logger")
    logger.info(response)
    return response


# Reprocess unfinished tasks for wheels
@task(
    name="process_unfinished_wheels",
    max_retries=2,
    retry_delay=timedelta(minutes=5),
    state_handlers=[handler]
)
def process_unfinished_wheels():
    response = docker.from_env().containers.run(
        image=docker_image,
        working_dir="/app",
        command=f"./provider_runtool.py --provider 'wheels' --time-min '{time_min}' --time-max '{time_max}' --incomplete-only --no-logs",
        environment=environment_variables,
        volumes=None,
        remove=True,
        detach=False,
        stdout=True
    ).decode("utf-8")
    logger = prefect.context.get("logger")
    logger.info(response)
    return response


# Reprocess unfinished tasks for wheels
@task(
    name="process_unfinished_scoobi",
    max_retries=2,
    retry_delay=timedelta(minutes=5),
    state_handlers=[handler]
)
def process_unfinished_scoobi():
    response = docker.from_env().containers.run(
        image=docker_image,
        working_dir="/app",
        command=f"./provider_runtool.py --provider 'scoobi' --time-min '{time_min}' --time-max '{time_max}' --incomplete-only --no-logs",
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
    f"atd_mds_unfinished_{current_environment}",
    # Let's configure the agents to download the file from this repo
    storage=GitHub(
        repo="cityofaustin/atd-prefect",
        path="flows/MDS/unfinished.py",
        ref=current_environment.replace("staging", "main"),  # The branch name
    ),
    # Run config will always need the current_environment
    # plus whatever labels you need to attach to this flow
    run_config=UniversalRun(
        labels=[current_environment, "atd-data02"]
    ),
    schedule=Schedule(clocks=[CronClock("0 2 * * *")])
) as flow:
    """
        While there is nothing stopping us from having
        the tasks run concurrently, I would argue it is best
        to keep them chained. This is to not overwhelm the
        Hasura database, it is very small.
    """
    flow.chain(
        process_unfinished_lime,
        process_unfinished_bird,
        process_unfinished_wheels,
        process_unfinished_scoobi,
    )

if __name__ == "__main__":
    flow.run()
