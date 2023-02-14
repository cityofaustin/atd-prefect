#!/usr/bin/env python

"""
Name: Knack Banner HR App integration
Description: Update knack HR app based on records in Banner and CTM
Schedule: "45 13 * * *"
Labels: atd-data02, knack
"""


'''

'''
import prefect
# import os
import docker
# from datetime import datetime, timedelta

# Prefect
from prefect import flow, task, get_run_logger
from prefect.blocks.notifications import SlackWebhook
from prefect.blocks.system import JSON
# from prefect.engine.results import PrefectResult
# from prefect.tasks.prefect import create_flow_run, get_task_run_result
# from prefect.storage import GitHub
# from prefect.run_configs import UniversalRun
# from prefect.engine.state import Failed, TriggerFailed, Retrying
# from prefect.schedules import Schedule
# from prefect.schedules.clocks import CronClock
# from prefect.backend import get_key_value
# from prefect.triggers import all_successful

# from prefect.tasks.notifications.email_task import EmailTask

docker_image = f"atddocker/atd-knack-banner:production"

# # Retrieve the email configuration
# email_config = get_key_value(key="aws_email_config")


slack_webhook_block = SlackWebhook.load("slack-failure-notification")






# # Configure email task
# email_task = EmailTask(
#     name="email_task",
#     subject="Knack HR updates from Banner",
#     email_to=environment_variables["EMAIL_ADDRESS"],
#     email_to_cc=environment_variables["EMAIL_ADDRESS_CC"],
#     email_from=email_config["email_from"],
#     smtp_server=email_config["smtp_server"],
#     smtp_port=email_config["smtp_port"],
#     smtp_type=email_config["smtp_type"],
#     attachments=None,
# )


# @task(log_stdout=True, state_handlers=[handler])
# def format_email_body(flow_data):
#     flow_data_list = flow_data.split("\n")
#     info_list = []
#     # only email the logs that are labeled "INFO:root"
#     for line in flow_data_list:
#         if line[0:9] == "INFO:root":
#             info_list.append(line[10:] + "<br>")
#     return " ".join(info_list)


# with Flow(
#     f"atd_knack_banner_{current_environment}",
#     storage=GitHub(
#         repo="cityofaustin/atd-prefect",
#         path="flows/knack/knack_banner.py",
#         ref="main"
#     ),
#     run_config=UniversalRun(labels=[current_environment, "atd-data02"]),
#     result=PrefectResult(),
#     schedule=Schedule(clocks=[CronClock("45 13 * * *")])
# ) as get_data_flow:
#     email_data = knack_banner_update_employees()


# with Flow(
#     f"send_hr_email_{current_environment}",
#     storage=GitHub(
#         repo="cityofaustin/atd-prefect",
#         path="flows/knack/knack_banner.py",
#         ref="main"  # The branch name
#     ),
#     run_config=UniversalRun(labels=[current_environment, "atd-data02"]),
# ) as send_email_flow:
#     get_data_flow_run_id = create_flow_run(flow_name=get_data_flow.name)
#     script_result = get_task_run_result(
#         get_data_flow_run_id, task_slug="knack-banner-copy"
#     )
#     formatted_data = format_email_body(script_result)
#     send_email_flow.chain(script_result, formatted_data, email_task(msg=formatted_data))

@task(name="get_environment_variables") # do I need to put retries here?
def get_env_vars():
    # Environment Variables stored in JSON block in Prefect
    return JSON.load("atd-knack-banner")

# Retrieve the provider's data
@task(
    name="update HR employees in knack",
    # max_retries=2,
    # retry_delay=timedelta(minutes=5),
    # state_handlers=[handler],
    # slug="knack-banner",
)
def knack_banner_update_employees(environment_variables):
    logger = get_run_logger()
    response = (
        docker.from_env()
        .containers.run(
            image=docker_image,
            working_dir="/app",
            command=f"./atd-knack-banner/update_employees.py",
            environment=environment_variables.value,
            volumes=None,
            remove=True,
            detach=False,
            stdout=True,
        )
        .decode("utf-8")
    )
    logger.info(response)
    return response


@flow(name=f"Knack HR Banner")
def knack_hr_banner_flow():
    logger = get_run_logger()
    environment_variables = get_env_vars()
    knack_banner_update_employees(environment_variables)

    # slack_webhook_block.notify("Hello is this thing on")


if __name__ == "__main__":
    knack_hr_banner_flow()
