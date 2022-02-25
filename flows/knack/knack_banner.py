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
import json
from datetime import datetime, timedelta

# Prefect
from prefect import Flow, task
from prefect.engine.results import PrefectResult
from prefect.tasks.prefect import create_flow_run, get_task_run_result, wait_for_flow_run
from prefect.storage import GitHub
from prefect.run_configs import UniversalRun
from prefect.engine.state import Failed, TriggerFailed
from prefect.schedules import Schedule
from prefect.schedules.clocks import CronClock
from prefect.backend import get_key_value
from prefect.triggers import all_successful

from prefect.utilities.notifications import slack_notifier
from prefect.tasks.notifications.email_task import EmailTask

current_environment = os.getenv("PREFECT_CURRENT_ENVIRONMENT", "production")

# Set up slack fail handler
handler = slack_notifier(only_states=[Failed, TriggerFailed]) # todo, add a different state handler if it doesnt run at all

docker_image = f"atddocker/atd-knack-banner:{current_environment}"

# Retrieve the email configuration
email_config = get_key_value(key="aws_email_config")
environment_variables = get_key_value(key=f"atd_knack_banner_{current_environment}")


# Retrieve the provider's data
@task(
    name="HR knack banner integration",
    max_retries=3,
    retry_delay=timedelta(minutes=5),
    # state_handlers=[handler],
    # result=PrefectResult(),
    slug="knack-banner"
)
def knack_banner_update_employees():
    # https://stackoverflow.com/questions/54000979/docker-py-how-to-get-exit-code-returned-by-process-running-inside-container
    client = docker.from_env()
    container = client.containers.run(
        image=docker_image,
        working_dir="/app",
        command=f"./atd-knack-banner/update_employees.py",
        environment=environment_variables,
        volumes=None,
        # remove=True,
        detach=True,
        stdout=True
    )#.decode("utf-8")
    result = container.wait()
    container.remove()
    logger = prefect.context.get("logger")
    logger.info(result)
    return result
    # return response


email_task = EmailTask(
    name="email_task",
    subject="Test from ATD",
    email_to="chia.berry@austintexas.gov",  # <- Type your email here
    email_from=email_config["email_from"],
    smtp_server=email_config["smtp_server"],
    smtp_port=email_config["smtp_port"],
    smtp_type=email_config["smtp_type"],
    attachments=None
)


@task(log_stdout=True)
def format_email_body(flow_data):
    print(f"Got: {flow_data!r}")
    return json.dumps(flow_data)


with Flow(
    f"atd_knack_banner_{current_environment}",
    storage=GitHub(
        repo="cityofaustin/atd-prefect",
        path="flows/knack/knack_banner.py",
        ref="7368-knack-banner",
    ),
    run_config=UniversalRun(
        labels=[current_environment, "atd-data02"]
    ),
    result=PrefectResult()
    # schedule=Schedule(clocks=[CronClock("45 13 * * *")])
) as get_data_flow:
    email_data = knack_banner_update_employees()



with Flow(
    # Postfix the name of the flow with the environment it belongs to
    f"send_hr_email_{current_environment}",
    # Let's configure the agents to download the file from this repo
    storage=GitHub(
        repo="cityofaustin/atd-prefect",
        path="flows/test/knack_banner.py",
        ref="7368-knack-banner",  # The branch name
    ),
    # Run config will always need the current_environment
    # plus whatever labels you need to attach to this flow
    run_config=UniversalRun(
        labels=[current_environment, "atd-data02"]
    ),
) as send_email_flow:
    get_data_flow_run_id = create_flow_run(flow_name=get_data_flow.name)
    wait_for_data_flow_run = wait_for_flow_run(get_data_flow_run_id, raise_final_state="True")
    script_result = get_task_run_result(get_data_flow_run_id, task_slug="knack-banner-copy")
    formatted_data = format_email_body(script_result)
    script_result.set_upstream(wait_for_data_flow_run)
    send_email_flow.chain(script_result, formatted_data, email_task(msg=formatted_data))


if __name__ == "__main__":
    send_email_flow.run()
