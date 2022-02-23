#!/usr/bin/env python

"""
Name: Knack Banner HR App integration
Description: TODO
Schedule: "45 13 * * *"
Labels: atd-data02, knack
"""

import os
import docker
import prefect
from datetime import datetime, timedelta

# Prefect
from prefect import Flow, task
from prefect.storage import GitHub
from prefect.run_configs import UniversalRun
from prefect.engine.state import Failed, TriggerFailed
from prefect.schedules import Schedule
from prefect.schedules.clocks import CronClock
from prefect.backend import get_key_value
from prefect.triggers import all_successful

from prefect.utilities.notifications import slack_notifier

current_environment = os.getenv("PREFECT_CURRENT_ENVIRONMENT", "staging")

# Set up slack fail handler
handler = slack_notifier(only_states=[Failed, TriggerFailed]) # todo, add a different state handler if it doesnt run at all

docker_image = f"atddocker/atd-knack-banner:{current_environment}"
environment_variables = get_key_value(key=f"atd_knack_banner_{current_environment}")

# Retrieve the provider's data
@task(
    name="HR knack banner integration",
    max_retries=3,
    retry_delay=timedelta(minutes=5),
    # state_handlers=[handler],
)
def knack_banner_update_employees():
    response = docker.from_env().containers.run(
        image=docker_image,
        working_dir="/app",
        command=f"./atd-knack-banner/update_employees.py",
        environment=environment_variables,
        volumes=None,
        remove=True,
        detach=False,
        stdout=True
    ).decode("utf-8")
    logger = prefect.context.get("logger")
    logger.info(response)
    return response

with Flow(
    f"atd_knack_banner_{current_environment}",
    storage=GitHub(
        repo="cityofaustin/atd-prefect",
        path="flows/knack/knack_banner.py",
        ref=current_environment.replace("staging", "main"),
    ),
    run_config=UniversalRun(
        labels=[current_environment, "atd-data02"]
    ),
    # schedule=Schedule(clocks=[CronClock("45 13 * * *")])
) as flow:
    flow.chain(
        knack_banner_update_employees()
    )

if __name__ == "__main__":
    flow.run()
