"""
Name: ATD Service Bot: Intake Issues
Description: Sends new issue data from our service portal (knack) to our Github
Schedule: */3 * * * * (AKA once every 3 minutes)
Work queue concurrency limit: 1
prefect deployment build flows/atd-service-bot/intake_issues.py:intake \
    --cron "*/3 * * * *" --pool atd-data-03 -q atd-service-bot \
    --name "Service Bot: Intake Issues" -o "deployments/atd_service_bot_intake.yaml" \
    -sb github/atd-service-bot-staging --skip-upload \
    --description "Repo: https://github.com/cityofaustin/atd-service-bot, Sends new issue data from our service portal (knack) to our Github"
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
    return True


# Get the envrioment variables based on the given environment
@task(name="get_env_vars", timeout_seconds=60)
def get_env_vars(env):
    logger = get_run_logger()
    logger.info(f"Getting secret block for: {env}")

    # Environment Variables stored in secret block in Prefect
    secret_block = Secret.load(f"atd-service-bot-{env}")
    encoded_env_vars = secret_block.get()
    decoded_env_vars = json.loads(encoded_env_vars)

    logger.info(f"Received Prefect Environment Variables for: {env}")
    return decoded_env_vars


# Knack Issues to Github
@task(name="intake_new_issues", timeout_seconds=60)
def intake_new_issues(environment_variables, docker_image):
    logger = get_run_logger()

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


@flow(name="Service Bot: Intake Issues")
def intake(docker_tag="production", env="production"):
    """Intakes new issues from Knack to Github

    Keyword arguments:
    docker_tag -- the docker tag to use (default "production")
    env -- the environment to use (default "production")
    """
    # 1. Get secrets from Prefect KV Store
    environment_variables = get_env_vars(env)

    # 2. Pull latest docker image
    docker_image = pull_docker_image(docker_tag)

    # 3. Intake new issues to github
    intake_new_issues(environment_variables, docker_image)


if __name__ == "__main__":
    intake()
