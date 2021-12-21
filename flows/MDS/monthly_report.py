#!/usr/bin/env python

"""
Name: Monthly MDS Report
Description: Gathers MDS data and uploads to Knack.
Schedule: "40 7 3 * *"
Labels: atd-data02
"""

import os

# Prefect
from prefect import Flow, task
from prefect.storage import GitHub
from prefect.run_configs import UniversalRun
from prefect.engine.state import Failed
from prefect.schedules import Schedule
from prefect.schedules.clocks import CronClock
from prefect.backend import get_key_value

from prefect.utilities.notifications import slack_notifier

# Shell
from prefect.tasks.shell import ShellTask
from prefect.tasks.notifications.email_task import EmailTask


# First, we must always define the current environment, and default to staging:
current_environment = os.getenv("PREFECT_CURRENT_ENVIRONMENT", "staging")

# Set up slack fail handler
handler = slack_notifier(only_states=[Failed])

# Notice how test_kv is an object that contains our data as a dictionary:
docker_image = f"atddocker/atd-mds-etl:{current_environment}"
environment_variables = get_key_value(key=f"atd_mds_monthly_report_{current_environment}")
email_config = get_key_value(key="aws_email_config")


# Sync the data with socrata
run_python = ShellTask(
    name="run_python_script",
    command="python3 ~/flows/MDS/python_scripts/atd_mds_monthly_report.py",
    env=environment_variables,
    stream_output=True
)

"""
Task for sending email from an authenticated email service over SMTP.
For this task to function properly you must have the "EMAIL_USERNAME" and "EMAIL_PASSWORD" set in Prefect.
"""
email_task = EmailTask(
    name="email_task",
    subject="MDS data inserted in Knack",
    msg="The MDS data has been inserted into Knack without errors.",
    email_to=environment_variables["email_recipients"],  # <- Type your email here
    email_from=email_config["email_from"],
    smtp_server=email_config["smtp_server"],
    smtp_port=email_config["smtp_port"],
    smtp_type=email_config["smtp_type"],
    attachments=None
)


# Next, we define the flow (equivalent to a DAG).
# Notice we use the label "test" to match this flow to an agent.
with Flow(
    # Postfix the name of the flow with the environment it belongs to
    f"atd_mds_monthly_report_{current_environment}",
    # Let's configure the agents to download the file from this repo
    storage=GitHub(
        repo="cityofaustin/atd-prefect",
        path="flows/MDS/monthly_report.py",
        ref=current_environment.replace("staging", "main"),  # The branch name
    ),
    # Run config will always need the current_environment
    # plus whatever labels you need to attach to this flow
    run_config=UniversalRun(
        labels=[current_environment, "atd-data02"]
    ),
    schedule=Schedule(clocks=[CronClock("40 7 3 * *")])
) as flow:
    flow.chain(
        run_python,
        email_task
    )

if __name__ == "__main__":
    flow.run()
