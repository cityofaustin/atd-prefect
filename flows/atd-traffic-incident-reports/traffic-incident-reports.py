#!/usr/bin/env python

"""
Name: Traffic Incident Reports to postgrest
Description: wrapper etl for atd-traffic-incident-reports docker image \
connects to oracle db and updates postrgrest with incidents
Schedule: "*/5 * * * *"

Create Deployment:
$ prefect deployment build flows/atd-traffic-incident-reports/traffic-incident-reports.py:traffic_incidents_flow \
--name "Austin Travis County Traffic Incident Reports" --pool atd-data-03 \
--cron "*/5 * * * *" -q default -sb github/atd-prefect-main-branch \
--description "Wrapper ETL for the https://github.com/cityofaustin/atd-traffic-incident-reports docker image connects to oracle db and updates postrgrest with incidents" \
-o "deployments/traffic-incident-reports.yaml" --skip-upload
 
$ prefect deployment apply deployments/traffic-incident-reports.yaml

"""

import prefect
import docker
from datetime import datetime, timedelta

# Prefect
from prefect import flow, task, get_run_logger
from prefect.blocks.system import JSON

# Docker settings
docker_env = "production"
docker_image = f"atddocker/atd-traffic-incident-reports:{docker_env}"


@task(
    name="get_env_vars",
    retries=10,
    retry_delay_seconds=timedelta(seconds=15).seconds,
)
def get_env_vars():
    # Environment Variables stored in JSON block in Prefect
    return JSON.load("atd-traffic-incident-reports").dict()["value"]


@task(
    name="pull_docker_image",
    retries=1,
    retry_delay_seconds=timedelta(minutes=5).seconds,
)
def pull_docker_image():
    client = docker.from_env()
    client.images.pull(docker_image)
    return True


# Retrieve the provider's data
@task(
    name="update_postgrest_with_traffic_incidents",
    retries=1,
    retry_delay_seconds=30,
)
def get_traffic_incidents(environment_variables):
    logger = get_run_logger()
    response = (
        docker.from_env()
        .containers.run(
            image=docker_image,
            working_dir="/app",
            command=f"python main.py",
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


@flow(name=f"Traffic Incidents")
def traffic_incidents_flow():
    environment_variables = get_env_vars()
    get_traffic_incidents(environment_variables)


if __name__ == "__main__":
    traffic_incidents_flow()
