import json
import docker

from prefect import task, get_run_logger
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
