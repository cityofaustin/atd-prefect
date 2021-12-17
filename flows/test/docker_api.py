#!/usr/bin/env python

"""
Name: Run a docker container and capture output
Description: A test on how to run a docker container using docker-py API
Schedule: None
Labels: test
"""

import os
import pathlib
import prefect

# Prefect
from prefect import Flow, task
from prefect.storage import GitHub
from prefect.run_configs import UniversalRun

# Docker-py low-level API
import docker

# First, we must always define the current environment, and default to staging:
current_environment = os.getenv("PREFECT_CURRENT_ENVIRONMENT", "staging")

environment_variables = {
    "MESSAGE": "HELLO WORLD"
}


# Second method, using docker low-level api
@task(name="docker_with_api")
def docker_with_api():
    client = docker.from_env()

    response = client.containers.run(
        image="python:alpine",
        working_dir="/app",
        command="python example.py",
        environment=environment_variables,
        volumes=[f"{pathlib.Path(__file__).parent.resolve()}/scripts:/app"],
        remove=True,
        detach=False,
        stdout=True
    ).decode("utf-8")

    logger = prefect.context.get("logger")
    logger.info(response)

    return response


with Flow(
    f"docker_api_{current_environment}",
    storage=GitHub(
        repo="cityofaustin/atd-prefect",
        path="flows/test/docker_api.py",
        ref=current_environment.replace("staging", "main"),  # The branch name
    ),
    run_config=UniversalRun(labels=[current_environment, "atd-prefect-01"])
) as flow:
    flow.add_task(docker_with_api)

if __name__ == "__main__":
    flow.run()
