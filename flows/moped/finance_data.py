#!/usr/bin/env python

"""
Name: ATD Finance Data Flow
Description: Gets finance data from S3 and places it in a Socrata dataset.
Schedule: "30 12 * * *"
Labels: atd-data02, moped
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
from prefect.backend import set_key_value, get_key_value
from prefect.triggers import all_successful

from prefect.utilities.notifications import slack_notifier

# Will be production or staging
current_environment = os.getenv("PREFECT_CURRENT_ENVIRONMENT", "staging")

# Set up slack fail handler
handler = slack_notifier(only_states=[Failed])

# Logger instance
logger = prefect.context.get("logger")

# Docker settings
docker_env = "production"
docker_image = f"atddocker/atd-finance-data:{docker_env}"

# Environment Variables from KV Store in Prefect
environment_variables = get_key_value(key=f"atd_finance_data")


@task(
    name="pull_docker_image",
    max_retries=1,
    timeout=timedelta(minutes=60),
    retry_delay=timedelta(minutes=5),
    state_handlers=[handler],
)
def pull_docker_image():
    client = docker.from_env()
    client.images.pull("atddocker/atd-finance-data", all_tags=True)
    logger.info(docker_image)
    return


@task(
    name="s3_to_socrata",
    max_retries=1,
    timeout=timedelta(minutes=60),
    retry_delay=timedelta(minutes=5),
    state_handlers=[handler],
)
def s3_to_socrata():
    response = (
        docker.from_env()
        .containers.run(
            image=docker_image,
            working_dir=None,
            command="python s3_to_socrata.py",
            environment=environment_variables,
            volumes=None,
            remove=True,
            detach=False,
            stdout=True,
        )
        .decode("utf-8")
    )
    logger.info(response)
    return response


with Flow(
    # Postfix the name of the flow with the environment it belongs to
    f"atd_finance_{current_environment}",
    # Let's configure the agents to download the file from this repo
    storage=GitHub(
        repo="cityofaustin/atd-prefect",
        path="flows/moped/finance_data.py",
        ref=current_environment.replace(
            "staging", "atd-finance-prod"
        ),  # The branch name
    ),
    # Run config will always need the current_environment
    # plus whatever labels you need to attach to this flow
    run_config=UniversalRun(labels=["test", "atd-data02"]),
    schedule=Schedule(clocks=[CronClock("30 12 * * *")]),
) as flow:
    flow.chain(pull_docker_image, s3_to_socrata)

if __name__ == "__main__":
    flow.run()
