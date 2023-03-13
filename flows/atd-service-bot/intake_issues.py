"""
Name: ATD Service Bot: Intake Issues
Description: Sends new issue data from our service portal (knack) to our Github
Schedule: */3 * * * * (AKA once every 3 minutes)
prefect deployment build flows/atd-service-bot/intake_issues.py:main -t test \
    --cron "*/3 * * * *" --pool atd-data-03 -q default \
    --name "Service Bot: Intake Issues" -o "deployments/atd-service-bot-intake.yaml" \
    -sb github/atd-prefect-main-branch --skip-upload \
    --description "Repo: https://github.com/cityofaustin/atd-service-bot, Sends new issue data from our service portal (knack) to our Github"
"""

import docker
import prefect
from datetime import timedelta
import json


# Prefect
from prefect import flow, task
from prefect.engine.state import Failed
from prefect.blocks.system import Secret


from prefect.utilities.notifications import slack_notifier

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
    client.images.pull("atddocker/atd-service-bot", tag=docker_tag)
    logger.info(f"Docker Images Pulled, using: {docker_image}")
    return docker_image


# Get the envrioment variables based on the given environment
@task(
    name="get_env_vars",
    timeout=timedelta(minutes=1),
    state_handlers=[handler],
    log_stdout=True,
)
def get_env_vars(env):
    # Environment Variables stored in secret block in Prefect
    secret_block = Secret.load(f"atd-service-bot-{env}")
    encoded_env_vars = secret_block.get()
    decoded_env_vars = json.loads(encoded_env_vars)

    logger.info(f"Received Prefect Environment Variables for: {env}")
    return decoded_env_vars


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


# TODO: Figure out storage block in deployment build command. Skip upload?
# TODO: What about pools and queues? Can we use these to organize flows?


@flow(name="Service Bot: Intake Issues")
def intake(docker_tag="test", env="production"):
    """Intakes new issues from Knack to Github

    Keyword arguments:
    docker_tag -- the docker tag to use (default "test")
    env -- the environment to use (default "production")
    """

    # 1. Get secrets from Prefect KV Store
    environment_variables = get_env_vars(env)

    # 2. Pull latest docker image
    docker_image = pull_docker_image(docker_tag)

    # 3. Intake new issues to github
    res = intake_new_issues(environment_variables, docker_image)


if __name__ == "__main__":
    intake()
