#!/usr/bin/env python

"""
Name: ATD Service Bot: Intake Issues
Description: Sends new issue data from our service portal (knack) to our Github
Repo atd-data-tech
Schedule: * * * * * (AKA once every minute)
Labels: WIP
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

# Select the appropriate tag for the Docker Image
# docker_env will also be taken as a parameter
DOCKER_TAG = "test"

# Envrioment vars
ENV = "production"

# Set up slack fail handler
handler = slack_notifier(only_states=[Failed])

# Logger instance
logger = prefect.context.get("logger")

# Task to pull the latest Docker image
@task(
    name="pull_docker_image",
    timeout=timedelta(minutes=1),
    state_handlers=[handler],
    log_stdout=True,
)
def pull_docker_image(docker_tag):
    docker_image = f"atddocker/atd-service-bot:{docker_tag}"
    client = docker.from_env()
    response = client.images.pull("atddocker/atd-service-bot", tag=docker_tag)
    logger.info(f"Docker Images Pulled, using: {docker_image}")
    return docker_image


# Get the envrioment variables based on the given environment
@task(
    name="get_env_vars",
    timeout=timedelta(minutes=1),
    state_handlers=[handler],
    log_stdout=True,
)
def get_env_vars():
    environment_variables = get_key_value(key=f"atd_service_bot_{ENV}")
    logger.info(f"Recieved Prefect Environment Variables for: {docker_image}")
    return environment_variables


# Knack Issues to Github
@task(
    name="intake_new_issues",
    timeout=timedelta(minutes=1),
    state_handlers=[handler],
    log_stdout=True,
)
def intake_new_issues(environment_variables, docker_image):
    response = (
        docker.from_env()
        .containers.run(
            image=docker_image,
            working_dir=None,
            command=f"python atd-service-bot/intake.py",
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


with Flow(
    # Flow Name
    "Service Bot: Intake Issues",
    # Let's configure the agents to download the file from this repo
    storage=GitHub(
        repo="cityofaustin/atd-prefect",
        path="flows/service-bot/intake_issues.py",
        ref="ch-atd-service-bot",  # The branch name
        access_token_secret="GITHUB_ACCESS_TOKEN"
    ),
    run_config=LocalRun(labels=["atd-data02", "test"]),
    schedule=None,
) as flow:
    # Parameter task
    docker_tag = Parameter(
        "Tag of the atd-service-bot Docker image", default=DOCKER_TAG, required=True
    )

    # 1. Get secrets from Prefect KV Store
    environment_variables = get_env_vars()

    # 2. Pull latest docker image
    docker_image = pull_docker_image(docker_tag)

    # 3. Intake new issues to github
    res = intake_new_issues(environment_variables, docker_image)

if __name__ == "__main__":
    flow.run(
        parameters={"Docker image tag": DOCKER_TAG,}
    )
