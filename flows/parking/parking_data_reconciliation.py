#!/usr/bin/env python

"""
Name: Parking Data Reconciliation Flows
Description: Parse Fiserv emails then upsert the CSVs to a postgres DB.
    Grab the payment data retrived from flowbird and upsert that to a postgres DB.
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
from prefect.tasks.docker import PullImage


from prefect.utilities.notifications import slack_notifier

# Define current environment
current_environment = "production"

# Set up slack fail handler
handler = slack_notifier(only_states=[Failed])

# Logger instance
logger = prefect.context.get("logger")

# Select the appropriate tag for the Docker Image
docker_env = "production"
docker_image = f"atddocker/atd-parking-data-meters:{docker_env}"

environment_variables = get_key_value(key=f"atd_parking_data_meters")

# Last execution date
prev_execution_key = f"parking_data_reconciliation_prev_exec"
prev_execution_date_success = get_key_value(prev_execution_key)


def decide_prev_month(prev_execution_date_success):
    """
    Determines if the current month or the current plus previous month S3 
        folders are needed. If it is within a week of the previous month,
        also upsert that months data.
    Parameters
    ----------
    prev_execution_date_success : String
        Last date the flow was successful.

    Returns
    -------
    Prev_month : Bool
        Argument if the previous month should be run.

    """
    if prev_execution_date_success:
        last_date = datetime.strptime(prev_execution_date_success, "%Y-%m-%d")
        # If in the first 8 days of the month of last few days of the month re-run
        # the previous month's data to make sure it is complete.
        if last_date.day < 8 or last_date.day > 26:
            return True
        else:
            return False
    return True


prev_month = decide_prev_month(prev_execution_date_success)

# Task to pull the latest Docker image
@task(
    name="pull_docker_image",
    max_retries=1,
    timeout=timedelta(minutes=60),
    retry_delay=timedelta(minutes=5),
    state_handlers=[handler],
    log_stdout=True
)
def pull_docker_image():
    client = docker.from_env()
    client.images.pull("atddocker/atd-parking-data-meters", all_tags=True)
    logger.info(docker_env)
    return


# First, process the latest emails from Fiserv in S3
@task(
    name="fiserv_email_parse",
    max_retries=1,
    timeout=timedelta(minutes=60),
    retry_delay=timedelta(minutes=5),
    state_handlers=[handler],
    log_stdout=True
)
def fiserv_email_parse():
    response = (
        docker.from_env()
        .containers.run(
            image=docker_image,
            working_dir=None,
            command="python fiserv_email_pub.py",
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


# Upload the emails to the database
@task(
    name="fiserv_emails_to_db",
    max_retries=1,
    timeout=timedelta(minutes=60),
    retry_delay=timedelta(minutes=5),
    state_handlers=[handler],
    trigger=all_successful,
    log_stdout=True
)
def fiserv_emails_to_db():
    response = (
        docker.from_env()
        .containers.run(
            image=docker_image,
            working_dir=None,
            command=f"python fiserv_DB.py --lastmonth {prev_month}",
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


# Upload the ATD payment CSVs to postgres
@task(
    name="payment_csv_to_db",
    max_retries=1,
    timeout=timedelta(minutes=60),
    retry_delay=timedelta(minutes=5),
    state_handlers=[handler],
    trigger=all_successful,
    log_stdout=True
)
def payment_csv_to_db():
    response = (
        docker.from_env()
        .containers.run(
            image=docker_image,
            working_dir=None,
            command=f"python payments_s3.py --lastmonth {prev_month}",
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

# Upload the PARD payment CSVs to postgres
@task(
    name="pard_payment_csv_to_db",
    max_retries=1,
    timeout=timedelta(minutes=60),
    retry_delay=timedelta(minutes=5),
    state_handlers=[handler],
    trigger=all_successful,
    log_stdout=True
)
def pard_payment_csv_to_db():
    response = (
        docker.from_env()
        .containers.run(
            image=docker_image,
            working_dir=None,
            command=f"python payments_s3.py --lastmonth {prev_month} --user pard",
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


# Upload the Passport app data CSVs to postgres
@task(
    name="app_data_to_db",
    max_retries=1,
    timeout=timedelta(minutes=60),
    retry_delay=timedelta(minutes=5),
    state_handlers=[handler],
    trigger=all_successful,
    log_stdout=True
)
def app_data_to_db():
    response = (
        docker.from_env()
        .containers.run(
            image=docker_image,
            working_dir=None,
            command=f"python passport_DB.py --lastmonth {prev_month}",
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


# Upload the smartfolio transactions CSVs to postgres
@task(
    name="smartfolio_csv_to_db",
    max_retries=1,
    timeout=timedelta(minutes=60),
    retry_delay=timedelta(minutes=5),
    state_handlers=[handler],
    trigger=all_successful,
    log_stdout=True
)
def smartfolio_csv_to_db():
    response = (
        docker.from_env()
        .containers.run(
            image=docker_image,
            working_dir=None,
            command=f"python smartfolio_s3.py --lastmonth {prev_month}",
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


# Match the payments to the fiserv reports
@task(
    name="matching_transactions",
    max_retries=1,
    timeout=timedelta(minutes=60),
    retry_delay=timedelta(minutes=5),
    state_handlers=[handler],
    trigger=all_successful,
    log_stdout=True
)
def matching_transactions():
    response = (
        docker.from_env()
        .containers.run(
            image=docker_image,
            working_dir=None,
            command=f"python match_field_processing.py",
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


# Uploading payments records to socrata dataset
@task(
    name="payments_to_socrata",
    max_retries=1,
    timeout=timedelta(minutes=60),
    retry_delay=timedelta(minutes=5),
    state_handlers=[handler],
    trigger=all_successful,
    log_stdout=True
)
def payments_to_socrata():
    response = (
        docker.from_env()
        .containers.run(
            image=docker_image,
            working_dir=None,
            command=f"python parking_socrata.py --dataset payments",
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


# Uploading Fiserv records to socrata dataset
@task(
    name="fiserv_to_socrata",
    max_retries=1,
    timeout=timedelta(minutes=60),
    retry_delay=timedelta(minutes=5),
    state_handlers=[handler],
    trigger=all_successful,
    log_stdout=True
)
def fiserv_to_socrata():
    response = (
        docker.from_env()
        .containers.run(
            image=docker_image,
            working_dir=None,
            command=f"python parking_socrata.py --dataset fiserv",
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


# Uploading Parking transactions records to public socrata dataset
@task(
    name="transactions_to_socrata",
    max_retries=1,
    timeout=timedelta(minutes=60),
    retry_delay=timedelta(minutes=5),
    state_handlers=[handler],
    trigger=all_successful,
    log_stdout=True
)
def transactions_to_socrata():
    response = (
        docker.from_env()
        .containers.run(
            image=docker_image,
            working_dir=None,
            command=f"python parking_socrata.py --dataset transactions",
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
    f"parking_data_reconciliation_{current_environment}",
    # Let's configure the agents to download the file from this repo
    storage=GitHub(
        repo="cityofaustin/atd-prefect",
        path="flows/parking/parking_data_reconciliation.py",
        ref="production",  # The branch name
    ),
    # Run config will always need the current_environment
    # plus whatever labels you need to attach to this flow
    run_config=UniversalRun(labels=[current_environment, "atd-data02"]),
    schedule=Schedule(clocks=[CronClock("00 5 * * *")]),
) as flow:
    flow.chain(
        pull_docker_image,
        fiserv_email_parse,
        fiserv_emails_to_db,
        payment_csv_to_db,
        pard_payment_csv_to_db,
        app_data_to_db,
        matching_transactions,
        smartfolio_csv_to_db,
        payments_to_socrata,
        fiserv_to_socrata,
        transactions_to_socrata,
        update_last_exec_time,
    )


if __name__ == "__main__":
    flow.run()
