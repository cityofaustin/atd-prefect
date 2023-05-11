#!/usr/bin/env python

"""
Name: Knack Services: Artbox Signals
Description: Repo: https://github.com/cityofaustin/atd-knack-services Wrapper ETL for the atd-knack-services docker image 
             with commands for updating signal records in one knack app (smart mobility) with data from another (data tracker).

Create Deployment:
$ prefect deployment build flows/atd-knack-services/atd_knack_artbox_signals.py:main \
    --name "Knack Services: Artbox Signals" \
    --pool atd-data-03 \
    --cron "30 0 * * *" \
    -q default \
    -sb github/atd-prefect-main-branch \
    -o "deployments/atd_knack_artbox_signals.yaml" \
    --description "Repo: https://github.com/cityofaustin/atd-knack-services Wrapper ETL for the atd-knack-services docker image with commands for updating signal records in one knack app (smart mobility) with data from another (data tracker)." \
    --skip-upload \
    --tag atd-knack-services
 
$ prefect deployment apply deployments/atd_knack_artbox_signals.yaml
"""

import os

import docker
import prefect
from datetime import datetime, timedelta

# Prefect
from prefect import flow, task, get_run_logger
from prefect.blocks.system import JSON

FLOW_NAME = "Knack Services: Artbox Signals"

# Docker settings
docker_env = "production"
docker_image = "atddocker/atd-knack-services"


@task(
    name="get_env_vars",
    retries=10,
    retry_delay_seconds=timedelta(seconds=15).seconds,
)
def get_env_vars(json_block):
    # Environment Variables stored in JSON block in Prefect
    return JSON.load(json_block).dict()["value"]


@task(
    name="pull_docker_image",
    retries=1,
    retry_delay_seconds=timedelta(minutes=5).seconds,
)
def pull_docker_image():
    client = docker.from_env()
    client.images.pull(docker_image, tag=docker_env)
    return True


# Determine what date to run the knack scripts
@task(
    name="determine_date_args",
    retries=1,
    retry_delay_seconds=timedelta(minutes=5).seconds,
)
def determine_date_args(environment_variables, commands):
    # Completely replace data on 15th day of every month,
    # to catch records potentially missed by incremental refreshes
    output = []
    if datetime.today().day == 15:
        for c in commands:
            output.append(f"{c} -d 1970-01-01")
        return output

    prev_exec = environment_variables["PREV_EXECS"][FLOW_NAME]
    for c in commands:
        output.append(f"{c} -d {prev_exec}")
    return output


@task(
    name="docker_command",
    retries=1,
    retry_delay_seconds=timedelta(minutes=5).seconds,
)
def docker_command(environment_variables, command, logger):
    logger.info(command)
    response = (
        docker.from_env()
        .containers.run(
            image=f"{docker_image}:{docker_env}",
            working_dir=None,
            command=f"python {command}",
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


@task(
    name="update_exec_date",
    retries=10,
    retry_delay_seconds=timedelta(seconds=15).seconds,
)
def update_exec_date(json_block):
    # Update our JSON block with the updated date of last flow execution
    block = JSON.load(json_block)
    block.value["PREV_EXECS"][FLOW_NAME] = datetime.today().strftime("%Y-%m-%d")
    block.save(name=json_block, overwrite=True)


@flow(name=FLOW_NAME)
def main(commands, block, app_name_src, app_name_dest):
    # Logger instance
    logger = get_run_logger()

    # Start: get env vars and pull the latest docker image
    environment_variables = get_env_vars(block)
    docker_res = pull_docker_image()

    # Append date argument to our commands list
    commands = determine_date_args(environment_variables, commands)

    # Running provided commands
    # 1. Upload source data to postgres
    command_res = docker_command(
        environment_variables[app_name_src], commands[0], logger
    )

    # 2. Upload destination data to postgres
    command_res = docker_command(
        environment_variables[app_name_dest], commands[1], logger
    )

    # 3. Upload data to destination knack app
    command_res = docker_command(
        environment_variables[f"{app_name_src} to {app_name_dest}"], commands[2], logger
    )

    update_exec_date(block)


if __name__ == "__main__":
    app_name_src = "data-tracker"  # Name of source data knack app
    container_src = "view_197"  # Container of source

    app_name_dest = "smart-mobility"  # Name of destination data knack app
    container_dest = "view_396"  # Container of destination

    # List of commands to be sent to the docker image
    commands = [
        f"atd-knack-services/services/records_to_postgrest.py -a {app_name_src} -c {container_src}",
        f"atd-knack-services/services/records_to_postgrest.py -a {app_name_dest} -c {container_dest}",
        f"atd-knack-services/services/records_to_knack.py -a {app_name_src} -c {container_src} -dest {app_name_dest}",
    ]

    # Environment Variable Storage Block Name
    block = "atd-knack-services"

    main(commands, block, app_name_src, app_name_dest)
