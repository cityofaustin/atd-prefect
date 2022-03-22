#!/usr/bin/env python

"""
Name: Parking Data Reconciliation Flows
Description: Parse Fiserv emails then upsert the CSVs to a postgres DB.
    Grab the payment data retrived from flowbird and upsert tha to a postgres DB.
    Then, compare them before uploading the data to Socrata.
Schedule: "30 5 * * *"
Labels: atd-data02, parking
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


# First, we must always define the current environment, and default to staging:
# current_environment = os.getenv("PREFECT_CURRENT_ENVIRONMENT", "staging")

current_environment = "test"

# Set up slack fail handler
# handler = slack_notifier(only_states=[Failed])

docker_env = "latest"
docker_image = f"atddocker/atd-parking-data-meters:{docker_env}"

# Logger instance
logger = prefect.context.get("logger")

# Notice how test_kv is an object that contains our data as a dictionary:
env = "prod"  # if current_environment == "production" else "staging"
environment_variables = get_key_value(key="trail_counters")

# Last execution date
prev_execution_key = f"parking_data_reconciliation_prev_exec"
# prev_execution_date_success = get_key_value(prev_execution_key)

prev_execution_date_success = None


def get_start_date(prev_execution_date_success):
    """Creates a start date 7 days before the date of the last successful run of the flow 
    Args:
        prev_execution_date_success (string): Date of the last successful run of the flow 
        
    Returns:
        list: The start date (string) which is 7 days before the last run. 
        Defaults to 2021-12-25 if none were previously successful. 
    """
    if prev_execution_date_success:
        # parse CLI arg date
        start_date = datetime.strptime(prev_execution_date_success, "%Y-%m-%d")
        start_date = start_date - timedelta(days=7)

        return start_date.strftime("%Y-%m-%d")
    else:
        return "2014-01-01"


start_date = get_start_date(prev_execution_date_success)

# This script does everything, gets data and puts it in socrata.
@task(
    name="trail_counter_task",
    max_retries=1,
    timeout=timedelta(minutes=60),
    retry_delay=timedelta(minutes=5),
    # state_handlers=[handler],
)
def trail_counter_task():
    response = (
        docker.from_env()
        .containers.run(
            image=docker_image,
            working_dir=None,
            command=f"python counter_data.py --start {start_date}",
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


@task(trigger=all_successful)
def update_last_exec_time():
    new_date = datetime.today().strftime("%Y-%m-%d")
    set_key_value(key=prev_execution_key, value=new_date)


# Next, we define the flow (equivalent to a DAG).
# Notice we use the label "test" to match this flow to an agent.
with Flow(
    # Postfix the name of the flow with the environment it belongs to
    f"trail_counter_pub_{current_environment}",
    # Let's configure the agents to download the file from this repo
    storage=GitHub(
        repo="cityofaustin/atd-ped-bike-crash",
        path="counter_data.py",
        ref="trail-counters",  # The branch name
    ),
    # Run config will always need the current_environment
    # plus whatever labels you need to attach to this flow
    # run_config=UniversalRun(labels=[current_environment, "atd-data02"]),
    run_config=UniversalRun(labels=["test", "ATD-JRWJXM2-D1.coacd.org"]),
    schedule=Schedule(clocks=[CronClock("00 12 * * *")]),
) as flow:
    flow.chain(
        trail_counter_task,
        # update_last_exec_time,
    )


if __name__ == "__main__":
    flow.run()
