#!/usr/bin/env python

"""
Name: ATD Service Bot: Update Issues
Description: Updates projects in our DTS portal (Knack) with new data from Github
Schedule: 13 7 * * * (UTC)
Work queue concurrency limit: 1
prefect deployment build flows/atd-service-bot/update_issues.py:update \
    --cron "13 7 * * *" --pool atd-data-03 -q atd-service-bot \
    --name "Service Bot: Update Issues" -o "deployments/atd_service_bot_update.yaml" \
    -sb github/atd-service-bot-staging --skip-upload \
    --description "Repo: https://github.com/cityofaustin/atd-service-bot, Updates projects in our DTS portal (Knack) with new data from Github"
"""

import docker

# Prefect
from prefect import flow, task, get_run_logger

from helpers import get_env_vars, pull_docker_image

# Index Issues to Knack
@task(name="update_knack_issues", timeout_seconds=60)
def update_knack_issues(environment_variables, docker_image):
    logger = get_run_logger()

    response = (
        docker.from_env()
        .containers.run(
            image=docker_image,
            working_dir=None,
            command=f"python atd-service-bot/gh_index_issues_to_dts_portal.py",
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


@flow(name="Service Bot: Update Issues")
def update(docker_tag="production", env="production"):
    """Updates projects in our DTS portal (Knack) with new data from Github

    Keyword arguments:
    docker_tag -- the docker tag to use (default "production")
    env -- the environment to use (default "production")
    """
    # 1. Get secrets from Prefect KV Store
    environment_variables = get_env_vars(env)

    # 2. Pull latest docker image
    docker_image = pull_docker_image(docker_tag)

    # 3. Update our issues
    update_knack_issues(environment_variables, docker_image)


if __name__ == "__main__":
    update()
