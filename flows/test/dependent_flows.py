#!/usr/bin/env python

"""
Name: Dependent flows testing
Description: The purpose of this file is to serve as a template to
    establish a pattern for the implementation of flows moving forward.
Labels: test
"""

import os
import prefect

# Prefect
from prefect import Flow, task
from prefect.tasks.prefect import create_flow_run, get_task_run_result
from prefect.storage import GitHub
from prefect.run_configs import UniversalRun
from prefect.engine.results import PrefectResult, LocalResult
from prefect.backend import get_key_value

from prefect.tasks.notifications.email_task import EmailTask

# First, we must always define the current environment, and default to staging:
current_environment = os.getenv("PREFECT_CURRENT_ENVIRONMENT", "staging")

# Notice how test_kv is an object that contains our data as a dictionary:
environment_variables = get_key_value(key=f"test_kv_{current_environment}")

# Retrieve the email configuration
email_config = get_key_value(key="aws_email_config")


@task(name="First", result=PrefectResult(), slug="first-slug")
def first():
    logger = prefect.context.get("logger")
    logger.info("ONE!!!")
    return {"users": "thing"}


email_task = EmailTask(
    name="email_task",
    subject="Test from ATD",
    msg="Hello this is a test from atd!",
    email_to="chia.berry@austintexas.gov",  # <- Type your email here
    email_from=email_config["email_from"],
    smtp_server=email_config["smtp_server"],
    smtp_port=email_config["smtp_port"],
    smtp_type=email_config["smtp_type"],
    attachments=None
)

with Flow(
    # Postfix the name of the flow with the environment it belongs to
    f"dependent_flow_one_{current_environment}",
    # Let's configure the agents to download the file from this repo
    # storage=GitHub(
    #     repo="cityofaustin/atd-prefect",
    #     path="flows/test/dependent_flows.py",
    #     ref=current_environment.replace("staging", "main"),  # The branch name
    # ),
    # Run config will always need the current_environment
    # plus whatever labels you need to attach to this flow
    run_config=UniversalRun(
        labels=[current_environment, "atd-data02"]
    ),
    result=PrefectResult()
) as first_flow:
    first_result = first()

with Flow(
    # Postfix the name of the flow with the environment it belongs to
    f"dependent_flows_email_{current_environment}",
    # Let's configure the agents to download the file from this repo
    # storage=GitHub(
    #     repo="cityofaustin/atd-prefect",
    #     path="flows/test/dependent_flows.py",
    #     ref=current_environment.replace("staging", "main"),  # The branch name
    # ),
    # Run config will always need the current_environment
    # plus whatever labels you need to attach to this flow
    run_config=UniversalRun(
        labels=[current_environment, "atd-data02"]
    ),
) as second_flow:
    first_flow_run_id = create_flow_run(flow_name=first_flow.name)
    first_data = get_task_run_result(first_flow_run_id, task_slug="first-slug")
    # email_message = Parameter("email_message", default="there was nothing")
    email_task(task_args=dict(msg=first_data))


if __name__ == "__main__":
    second_flow.run()
