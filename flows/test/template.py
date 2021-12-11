#!/usr/bin/env python

"""
Name: Test multiple features
Description: This flow is to test multiple features and serves as a template.
    So far this is a very early demonstration, and it is likely to change a lot.
Schedule: "*/5 * * * *"
Labels: test
"""

import docker
import prefect
import pathlib
from datetime import timedelta

# Prefect
from prefect import Flow, task, config
from prefect.run_configs import UniversalRun
from prefect.engine.state import Failed
from prefect.schedules import Schedule
from prefect.schedules.clocks import CronClock
from prefect.client import Secret

from prefect.utilities.notifications import slack_notifier
from prefect.tasks.notifications.email_task import EmailTask
from prefect.tasks.shell import ShellTask

# Set up slack fail handler
handler = slack_notifier(only_states=[Failed])


# Environment variables we define within here
environment_variables = {
    "MESSAGE": "HELLO WORLD"
}

# Notice how test_secret is actually already parsed,
# we can pass it automatically next time!
environment_variables_from_secret = Secret("test_secret").get()

# Run a shell command
shell_task = ShellTask(
    name="shell_task",
    command='echo "MESSAGE: ${MESSAGE}"',
    env=environment_variables,
    stream_output=True,
    state_handlers=[handler]
)

# Run a python command!
python_task = ShellTask(
    name="python_task",
    command='python3 ./flows/test/scripts/example.py',
    env=environment_variables,
    stream_output=True,
    state_handlers=[handler]
)


# Run docker!
@task(
    name="docker_with_api",
    max_retries=3,
    retry_delay=timedelta(seconds=60),
    state_handlers=[handler]
)
def docker_with_api():
    response = docker.from_env().containers.run(
        image="python:alpine",
        working_dir="/app",
        command="python example.py",
        environment=environment_variables_from_secret,
        volumes=[f"{pathlib.Path(__file__).parent.resolve()}/scripts:/app"],
        remove=True,
        detach=False,
        stdout=True
    ).decode("utf-8")

    logger = prefect.context.get("logger")
    logger.info(response)

    return response


email_task = EmailTask(
    name="email_task",
    subject="Test from ATD",
    msg="Hello this is a test from atd!",
    email_to=None,  # <- Type your email here
    email_from=config.email.email_from,
    smtp_server=config.email.smtp_server,
    smtp_port=config.email.smtp_port,
    smtp_type=config.email.smtp_type,
    attachments=None
)

# Next, we define the flow (equivalent to a DAG).
# Notice we use the label "test" to match this flow to an agent.
with Flow(
    "template",
    run_config=UniversalRun(labels=["test"]),
    schedule=Schedule(clocks=[CronClock("*/5 * * * *")])
) as flow:
    flow.chain(shell_task, python_task, docker_with_api, email_task)

if __name__ == "__main__":
    flow.run()
