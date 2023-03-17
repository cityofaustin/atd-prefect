#!/usr/bin/env python

"""
Name: ATD Service Bot: Issues to Socrata
Description: Uploads (replaces) github issue data from our atd-data-tech repo 
to an Open Data Portal dataset (AKA Socrata)
Schedule: 21 5 * * * (UTC)
Work queue concurrency limit: 1
prefect deployment build flows/atd-service-bot/intake_issues.py:intake \
    --cron "*/3 * * * *" --pool atd-data-03 -q atd-service-bot \
    --name "Service Bot: Issues to Socrata" -o "deployments/atd_service_bot_socrata.yaml" \
    -sb github/atd-service-bot-staging --skip-upload \
    --description "Repo: https://github.com/cityofaustin/atd-service-bot, Uploads (replaces) github issue data from our atd-data-tech repo 
to an Open Data Portal dataset (AKA Socrata)
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
    max_retries=1,
    timeout=timedelta(minutes=60),
    retry_delay=timedelta(minutes=5),
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
    task_run_name="get_env_vars",
    max_retries=1,
    timeout=timedelta(minutes=60),
    retry_delay=timedelta(minutes=5),
    state_handlers=[handler],
    log_stdout=True,
)
def get_env_vars():
    environment_variables = get_key_value(key=f"atd_service_bot_{ENV}")
    logger.info(f"Recieved Prefect Environment Variables for: {docker_image}")
    return environment_variables


# Issues to Socrata
@task(
    name="sending_issues_to_socrata",
    max_retries=1,
    timeout=timedelta(minutes=60),
    retry_delay=timedelta(minutes=5),
    state_handlers=[handler],
    log_stdout=True,
)
def sending_issues_to_socrata(environment_variables, docker_image):
    response = (
        docker.from_env()
        .containers.run(
            image=docker_image,
            working_dir=None,
            command=f"python atd-service-bot/issues_to_socrata.py",
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


# with Flow(
#     # Flow Name
#     "Service Bot: Issues to Open Data Portal",
#     # Let's configure the agents to download the file from this repo
#     storage=GitHub(
#         repo="cityofaustin/atd-prefect",
#         path="flows/service-bot/issues_to_socrata.py",
#         ref="main",  # The branch name
#         access_token_secret="GITHUB_ACCESS_TOKEN",
#     ),
#     run_config=LocalRun(labels=["atd-data02", "test"]),
# ) as flow:
@flow(name="Service Bot: Issues to Socrata")
def socrata(docker_tag="production", env="production"):
    """Uploads (replaces) github issue data from our atd-data-tech repo

    Keyword arguments:
    docker_tag -- the docker tag to use (default "production")
    env -- the environment to use (default "production")
    """
    # 1. Get secrets from Prefect KV Store
    environment_variables = get_env_vars()

    # 2. Pull latest docker image
    docker_image = pull_docker_image(docker_tag)

    # 3. Send issue data to Socrata
    res = sending_issues_to_socrata(environment_variables, docker_image)


if __name__ == "__main__":
    flow.run(
        parameters={
            "Docker image tag": DOCKER_TAG,
        }
    )
