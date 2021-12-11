#!/usr/bin/env python

"""
Name: Run a docker container and capture output
Description: A test on how to run a docker container using docker-py API
Schedule: None
Labels: test
"""

import pathlib
import prefect

# Prefect
from prefect import Flow, task
from prefect.run_configs import UniversalRun

# Docker-py low-level API
import docker

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
        "docker_api",
        run_config=UniversalRun(labels=["test"])
) as flow:
    flow.add_task(docker_with_api)

if __name__ == "__main__":
    flow.run()
