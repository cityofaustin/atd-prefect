#!/usr/bin/env python

import os
import docker
import json
from datetime import datetime, timedelta


docker_image = f"atddocker/atd-knack-banner:latest"


def knack_banner_update_employees():
    # client = docker.from_env()
    # container = client.containers.run(
    #   image=docker_image,
    #   working_dir="/app",
    #   command=,
    #   environment=environment_variables,
    #   volumes=None,
    #   detach=True,
    #   stdout=True
    # )
    #
    #
    response = docker.from_env().containers.run(
        image=docker_image,
        working_dir="/app",
        command=f"./atd-knack-banner/update_employees.py",
        environment=environment_variables,
        volumes=None,
        remove=True,
        detach=False,
        stdout=True
    ).decode("utf-8")
    print(response)
    return response
    # return {"test": "im testing"}


if __name__ == "__main__":
    print("im starting")
    knack_banner_update_employees()
