#!/usr/bin/env python

"""
Name: ATD Service Bot: Issues to Socrata
Description: Uploads (replaces) github issue data from our atd-data-tech repo 
to an Open Data Portal dataset (AKA Socrata)
Schedule: 21 5 * * * (UTC)
Work queue concurrency limit: 1
prefect deployment build flows/atd-service-bot/issues_to_socrata.py:issues_to_socrata \
    --cron "21 5 * * *" --pool atd-data-03 -q atd-service-bot \
    --name "Service Bot: Issues to Socrata" -o "deployments/atd_service_bot_socrata.yaml" \
    -sb github/atd-service-bot-staging --skip-upload \
    --description "Repo: https://github.com/cityofaustin/atd-service-bot, Uploads (replaces) github issue data from our atd-data-tech repo 
to an Open Data Portal dataset (AKA Socrata)
"""

import docker
import json


# Prefect
from prefect import flow, task, get_run_logger
from prefect.blocks.system import Secret


# Task to pull the latest Docker image
@task(
    name="pull_docker_image",
    retries=1,
    retry_delay_seconds=5,
)
def pull_docker_image(docker_tag):
    logger = get_run_logger()

    docker_image = f"atddocker/atd-service-bot:{docker_tag}"
    client = docker.from_env()
    client.images.pull("atddocker/atd-service-bot", tag=docker_tag)
    logger.info(f"Docker Images Pulled, using: {docker_image}")
    return docker_image


# Get the environment variables based on the given environment
@task(name="get_env_vars", timeout_seconds=60)
def get_env_vars(env):
    logger = get_run_logger()

    # Environment Variables stored in secret block in Prefect
    secret_block = Secret.load(f"atd-service-bot-{env}")
    env_vars_json_string = secret_block.get()
    environment_variables = json.loads(env_vars_json_string)

    logger.info(f"Received Prefect Environment Variables for: {env}")
    return environment_variables


# Issues to Socrata
@task(name="sending_issues_to_socrata", timeout_seconds=60)
def sending_issues_to_socrata(environment_variables, docker_image):
    logger = get_run_logger()

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


@flow(name="Service Bot: Issues to Socrata")
def issues_to_socrata(docker_tag="production", env="production"):
    """Uploads (replaces) github issue data from our atd-data-tech repo

    Keyword arguments:
    docker_tag -- the docker tag to use (default "production")
    env -- the environment to use (default "production")
    """
    # 1. Get secrets from Prefect KV Store
    environment_variables = get_env_vars(env)

    # 2. Pull latest docker image
    docker_image = pull_docker_image(docker_tag)

    # 3. Send issue data to Socrata
    sending_issues_to_socrata(environment_variables, docker_image)


if __name__ == "__main__":
    issues_to_socrata()
