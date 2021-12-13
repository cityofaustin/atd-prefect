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
from prefect import Flow, task
from prefect.storage import Local
from prefect.run_configs import UniversalRun
from prefect.engine.state import Failed
from prefect.schedules import Schedule
from prefect.schedules.clocks import CronClock
from prefect.backend import get_key_value

from prefect.utilities.notifications import slack_notifier
from prefect.tasks.notifications.email_task import EmailTask
from prefect.tasks.shell import ShellTask

# Set up slack fail handler
handler = slack_notifier(only_states=[Failed])


# Environment variables we define within here
environment_variables = {
    "MESSAGE": "HELLO WORLD"
}

# Notice how test_kv is actually already parsed,
# we can pass it automatically next time!
environment_variables_from_kv = get_key_value(key="test_kv")

email_config = get_key_value(key="email_config")

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
        environment=environment_variables_from_kv,
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
    email_to=email_config["test_email"],  # <- Type your email here
    email_from=email_config["email_from"],
    smtp_server=email_config["smtp_server"],
    smtp_port=email_config["smtp_port"],
    smtp_type=email_config["smtp_type"],
    attachments=None
)

# Next, we define the flow (equivalent to a DAG).
# Notice we use the label "test" to match this flow to an agent.
with Flow(
    "template",
    run_config=UniversalRun(labels=["test"]),
    # Schedule:
    #   When developing or troubleshooting a flow with a schedule
    #   you may want to disable it by exporting the global variable before execution:
    #       $ PREFECT__FLOWS__RUN_ON_SCHEDULE=false python flows/test/template.py
    #   Alternatively, you can do something like this:
    #       flow.run(run_on_schedule=False)
    schedule=Schedule(clocks=[CronClock("*/5 * * * *")])


) as flow:
    flow.chain(shell_task, python_task, docker_with_api, email_task)

if __name__ == "__main__":
    flow.storage = Local(directory=".")
    flow.run()
