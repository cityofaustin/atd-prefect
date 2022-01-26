#!/usr/bin/env python

"""
Name: AFD Incident Uploads
Description: This flow uploads AFD Incident Response CSVs (Contact: Gus D). 
    The data is emailed to Frank's email account daily ~ 6:31AM. From there it
    gets forwarded to a S3 bucket via AWS Simple Email Serivce.
Schedule: None
Labels: test
"""

import os
import docker
import prefect
import pathlib
from datetime import timedelta

# Prefect
from prefect import Flow, task
from prefect.storage import GitHub
from prefect.run_configs import UniversalRun
from prefect.engine.state import Failed
from prefect.schedules import Schedule
from prefect.schedules.clocks import CronClock
from prefect.backend import get_key_value

from prefect.utilities.notifications import slack_notifier
from prefect.tasks.notifications.email_task import EmailTask
from prefect.tasks.shell import ShellTask

# First, we must always define the current environment, and default to staging:
current_environment = os.getenv("PREFECT_CURRENT_ENVIRONMENT", "staging")

# Set up slack fail handler
handler = slack_notifier(only_states=[Failed])

# Notice how test_kv is an object that contains our data as a dictionary:
environment_variables = get_key_value(key=f"test_kv_{current_environment}")

# Retrieve the email configuration
email_config = get_key_value(key="aws_email_config")

# Run a python command!
python_task = ShellTask(
    name="python_task",
    command="python3 ./flows/vision_zero/python_scripts/vz_etl_process_afd_incident_data.py",
    env=environment_variables,
    stream_output=True,
    state_handlers=[handler],
)

email_task = EmailTask(
    name="email_task",
    subject="Test from ATD",
    msg="Hello this is a test from atd!",
    email_to="mateo.clarke@austintexas.gov",  # <- Type your email here
    email_from=email_config["email_from"],
    smtp_server=email_config["smtp_server"],
    smtp_port=email_config["smtp_port"],
    smtp_type=email_config["smtp_type"],
    attachments=None,
)

# Next, we define the flow (equivalent to a DAG).
# Notice we use the label "test" to match this flow to an agent.
with Flow(
    # Postfix the name of the flow with the environment it belongs to
    f"template_{current_environment}",
    # Let's configure the agents to download the file from this repo
    storage=GitHub(
        repo="cityofaustin/atd-prefect",
        path="flows/vision_zero/afd_incident_upload.py",
        ref=current_environment.replace("staging", "main"),  # The branch name
    ),
    # Run config will always need the current_environment
    # plus whatever labels you need to attach to this flow
    run_config=UniversalRun(labels=[current_environment, "atd-data02"]),
    # Schedule:
    #   When developing or troubleshooting a flow with a schedule
    #   you may want to disable it by exporting the global variable before execution:
    #       $ PREFECT__FLOWS__RUN_ON_SCHEDULE=false python flows/test/template.py
    #   Alternatively, you can do something like this:
    #       flow.run(run_on_schedule=False)
    schedule=Schedule(clocks=[CronClock("* * * * *")]),
) as flow:
    flow.chain(python_task, email_task)

if __name__ == "__main__":
    flow.run()
