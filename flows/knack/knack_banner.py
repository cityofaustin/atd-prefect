#!/usr/bin/env python

"""
Name: Knack Banner HR App integration
Description: Update knack HR app based on records in Banner and CTM
Schedule: "45 13 * * *"
Labels: atd-data02, knack
"""

import os
import docker
import prefect
from datetime import datetime, timedelta

# Prefect
from prefect import Flow, task
from prefect.engine.results import PrefectResult
from prefect.tasks.prefect import create_flow_run, get_task_run_result
from prefect.storage import GitHub
from prefect.run_configs import UniversalRun
from prefect.engine.state import Failed, TriggerFailed, Retrying
from prefect.schedules import Schedule
from prefect.schedules.clocks import CronClock
from prefect.backend import get_key_value
from prefect.triggers import all_successful

from prefect.utilities.notifications import slack_notifier
from prefect.tasks.notifications.email_task import EmailTask

current_environment = os.getenv("PREFECT_CURRENT_ENVIRONMENT", "production")

# Set up slack fail handler
handler = slack_notifier(only_states=[Failed, TriggerFailed, Retrying])

docker_image = f"atddocker/atd-knack-banner:{current_environment}"

# Retrieve the email configuration
email_config = get_key_value(key="aws_email_config")
environment_variables = get_key_value(key=f"atd_knack_banner_{current_environment}")


# Retrieve the provider's data
@task(
    name="HR knack banner integration",
    max_retries=2,
    retry_delay=timedelta(minutes=5),
    state_handlers=[handler],
    slug="knack-banner",
)
def knack_banner_update_employees():
    response = (
        docker.from_env()
        .containers.run(
            image=docker_image,
            working_dir="/app",
            command=f"./atd-knack-banner/update_employees.py",
            environment=environment_variables,
            volumes=None,
            remove=True,
            detach=False,
            stdout=True,
        )
        .decode("utf-8")
    )
    logger = prefect.context.get("logger")
    logger.info(response)
    return response


# Configure email task
email_task = EmailTask(
    name="email_task",
    subject="Knack HR updates from Banner",
    email_to=environment_variables["EMAIL_ADDRESS"],
    email_to_cc=environment_variables["EMAIL_ADDRESS_CC"],
    email_from=email_config["email_from"],
    smtp_server=email_config["smtp_server"],
    smtp_port=email_config["smtp_port"],
    smtp_type=email_config["smtp_type"],
    attachments=None,
)


@task(log_stdout=True, state_handlers=[handler])
def format_email_body(flow_data):
    flow_data_list = flow_data.split("\n")
    info_list = []
    # only email the logs that are labeled "INFO:root"
    for line in flow_data_list:
        if line[0:9] == "INFO:root":
            info_list.append(line[10:] + "<br>")
    return " ".join(info_list)


with Flow(
    f"atd_knack_banner_{current_environment}",
    storage=GitHub(
        repo="cityofaustin/atd-prefect",
        path="flows/knack/knack_banner.py",
        ref="main"
    ),
    run_config=UniversalRun(labels=[current_environment, "atd-data02"]),
    result=PrefectResult(),
    schedule=Schedule(clocks=[CronClock("45 13 * * *")])
) as get_data_flow:
    email_data = knack_banner_update_employees()


with Flow(
    f"send_hr_email_{current_environment}",
    storage=GitHub(
        repo="cityofaustin/atd-prefect",
        path="flows/knack/knack_banner.py",
        ref="main"  # The branch name
    ),
    run_config=UniversalRun(labels=[current_environment, "atd-data02"]),
) as send_email_flow:
    get_data_flow_run_id = create_flow_run(flow_name=get_data_flow.name)
    script_result = get_task_run_result(
        get_data_flow_run_id, task_slug="knack-banner-copy"
    )
    formatted_data = format_email_body(script_result)
    send_email_flow.chain(script_result, formatted_data, email_task(msg=formatted_data))


if __name__ == "__main__":
    send_email_flow.run()
