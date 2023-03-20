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
from prefect import Flow, task, Parameter
from prefect.storage import GitHub
from prefect.run_configs import LocalRun
from prefect.engine.state import Failed
from prefect.backend import get_key_value


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


# Index Issues to Knack
@task(
    name="update_knack_issues",
    max_retries=1,
    timeout=timedelta(minutes=60),
    retry_delay=timedelta(minutes=5),
    state_handlers=[handler],
    log_stdout=True,
)
def update_knack_issues(environment_variables, docker_image):
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


# with Flow(
#     # Flow Name
#     "Service Bot: Update Issues",
#     # Let's configure the agents to download the file from this repo
#     storage=GitHub(
#         repo="cityofaustin/atd-prefect",
#         path="flows/service-bot/update_issues.py",
#         ref="main",  # The branch name
#         access_token_secret="GITHUB_ACCESS_TOKEN",  # Key in our Prefect secrets
#         # Configured at: https://cloud.prefect.io/team/secrets
#     ),
#     run_config=LocalRun(labels=["atd-data02", "test"]),
# ) as flow:
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
    res = update_knack_issues(environment_variables, docker_image)


if __name__ == "__main__":
    update()
