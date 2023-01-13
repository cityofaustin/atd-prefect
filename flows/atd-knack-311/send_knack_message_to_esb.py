#!/usr/bin/env python

"""
Name: Send knack message to 311 via ESB
Description: This flow fetches activity records from Knack apps and sends them to 311. See repo for details.
Repo atd-knack-311
Schedule: 
Labels: 
"""

import docker
import prefect
from datetime import timedelta


# Prefect
from prefect import Flow, task, Parameter
from prefect.storage import GitHub
from prefect.run_configs import LocalRun
from prefect.engine.state import Failed
from prefect.backend import get_key_value


from prefect.utilities.notifications import slack_notifier


DEFAULT_ENV = "staging"
DOCKER_BASE_IMAGE = "atddocker/atd-knack-311"

# Set up slack fail handler
handler = slack_notifier(only_states=[Failed])

# Logger instance
logger = prefect.context.get("logger")

# Task to pull the latest Docker image
@task(
    name="send_knack_message_to_esb_pull_docker_image",
    timeout=timedelta(minutes=1),
    state_handlers=[handler],
    log_stdout=True,
)
def pull_docker_image(env):
    docker_image = f"{DOCKER_BASE_IMAGE}:{env}"
    client = docker.from_env()
    client.images.pull(DOCKER_BASE_IMAGE, tag=env)
    logger.info(f"Docker Images Pulled, using: {docker_image}")
    return docker_image


# Get the envrioment variables based on the given environment
@task(
    name="send_knack_message_to_esb_get_env_vars",
    timeout=timedelta(minutes=1),
    state_handlers=[handler],
    log_stdout=True,
)
def get_env_vars(env, app_name):
    keys = get_key_value(key=f"atd-knack-311")
    logger.info(f"Getting Prefect Environment Variables for: {app_name} - {env}")
    return keys[app_name][env]


# Run the main script
@task(
    name="send_knack_message_to_esb_main",
    timeout=timedelta(minutes=1),
    state_handlers=[handler],
    log_stdout=True,
)
def send_knack_messages_to_esb(*, env_vars, app_name, docker_image):
    response = (
        docker.from_env()
        .containers.run(
            image=docker_image,
            working_dir=None,
            command=f"python atd-knack-311/send_esb_message.py {app_name}",
            environment=env_vars,
            volumes=None,
            remove=True,
            detach=False,
            stdout=True,
        )
        .decode("utf-8")
    )
    logger.info(response)
    return response


with Flow(
    # Flow Name
    "atd-knack-311-send-knack-message-to-esb",
    storage=GitHub(
        repo="cityofaustin/atd-prefect",
        path="flows/atd-knack-311/send_knack_message_to_esb.py",
        ref="main",  # The branch name
        access_token_secret="GITHUB_ACCESS_TOKEN",
    ),
    run_config=LocalRun(labels=["atd-data02", "production"]),
) as flow:
    # Parameter task
    env = Parameter("env", default=DEFAULT_ENV, required=True)

    app_name = Parameter("app_name",  default="data-tracker", required=True)

    # 1. Get secrets from Prefect KV Store
    env_vars = get_env_vars(env, app_name)

    # 2. Pull latest docker image
    docker_image = pull_docker_image(env)

    # 3. Intake new issues to github
    res = send_knack_messages_to_esb(
        env_vars=env_vars, app_name=app_name, docker_image=docker_image
    )

if __name__ == "__main__":
    flow.run(parameters={"env": DEFAULT_ENV, "app_name": "data-tracker"})
