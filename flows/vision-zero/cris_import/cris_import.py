#!/usr/bin/python3

import os
import sys
import json
import shutil
import pprint
import time
import datetime
import tempfile

import docker
import sysrsync
from git import Repo
import prefect
from prefect import task, Flow
from prefect.schedules import Schedule
from prefect.schedules import IntervalSchedule
from prefect.backend.artifacts import create_markdown_artifact
from prefect.schedules.clocks import CronClock

from prefect.run_configs import UniversalRun
from prefect.utilities.debug import is_serializable


PWD = os.getenv("PWD")
SFTP_ENDPOINT = os.getenv("SFTP_ENDPOINT")
ZIP_PASSWORD = os.getenv("ZIP_PASSWORD")
RAW_AIRFLOW_CONFIG_JSON = os.getenv("RAW_AIRFLOW_CONFIG")
VZ_ETL_LOCATION = os.getenv("VZ_ETL_LOCATION")
RAW_AIRFLOW_CONFIG = json.loads(RAW_AIRFLOW_CONFIG_JSON)


pp = pprint.PrettyPrinter(indent=2)


@task
def pull_from_github():
    logger = prefect.context.get("logger")
    logger.info(sys._getframe().f_code.co_name + "()")
    repo = Repo(PWD)
    origin = repo.remotes[0]
    pull_result = origin.pull()

    # sms = repo.submodules
    # for sm in sms:
    # print(sm.remotes)

    return repo


@task(
    name="Download archive from SFTP Endpoint",
    slug="get-zips",
    max_retries=3,
    retry_delay=datetime.timedelta(minutes=2),
)
def download_extract_archives():
    logger = prefect.context.get("logger")
    logger.info(sys._getframe().f_code.co_name + "()")
    zip_tmpdir = tempfile.mkdtemp()
    sysrsync.run(
        verbose=True,
        options=["-a"],
        source_ssh=SFTP_ENDPOINT,
        source="/home/txdot/*zip",
        sync_source_contents=False,
        destination=zip_tmpdir,
    )
    logger.info("Temp Directory: " + zip_tmpdir)
    return zip_tmpdir


@task(
    name="Decrypt & extract zip archives",
    slug="decompress-zips",
    max_retries=3,
    retry_delay=datetime.timedelta(minutes=2),
    nout=1,
)
def unzip_archives(archives_directory):
    logger = prefect.context.get("logger")
    logger.info(sys._getframe().f_code.co_name + "()")
    extracted_csv_directories = []
    for filename in os.listdir(archives_directory):
        logger.info("File: " + filename)
        extract_tmpdir = tempfile.mkdtemp()
        unzip_command = f'7za -y -p{ZIP_PASSWORD} -o"{extract_tmpdir}" x "{archives_directory}/{filename}"'
        os.system(unzip_command)
        extracted_csv_directories.append(extract_tmpdir)
    return extracted_csv_directories


@task(
    name="Build VZ ETL Docker image (if updated)",
    slug="docker-build",
    checkpoint=False,
)
def build_docker_image(extracts):
    logger = prefect.context.get("logger")
    logger.info(sys._getframe().f_code.co_name + "()")
    docker_client = docker.from_env()
    build_result = docker_client.images.build(
        path=VZ_ETL_LOCATION, tag="vz-etl"
    )
    return build_result[0]


@task(
    name="Run VZ ETL Docker Image",
)
def run_docker_image(extracted_data, vz_etl_image, command):
    logger = prefect.context.get("logger")
    logger.info(sys._getframe().f_code.co_name + "()")

    docker_tmpdir = tempfile.mkdtemp()
    # return docker_tmpdir  # this is short circuiting out the rest of this routine (for speed of dev)
    volumes = {
        docker_tmpdir: {"bind": "/app/tmp", "mode": "rw"},
        extracted_data: {"bind": "/data", "mode": "rw"},
    }

    docker_client = docker.from_env()
    log = docker_client.containers.run(
        image=vz_etl_image,
        name="vz_etl",
        command=command,
        volumes=volumes,
        network_mode="host",  # This should be doable in bridged network mode. TODO: Investigate
        remove=True,
        environment=RAW_AIRFLOW_CONFIG,
    )
    logger.info(log)

    artifact = f"""
    # Imported {command[1]}

    ## Objects operated on
    ## TODO make docker container emit log as a JSON blob, parse it and then emit an artifact
    """    
    create_markdown_artifact(artifact)

    return docker_tmpdir


@task(name="Cleanup temporary directories", slug="cleanup-temporary-directories")
def cleanup_temporary_directories(single, list, container_tmpdirs):
    logger = prefect.context.get("logger")
    logger.info(sys._getframe().f_code.co_name + "()")
    shutil.rmtree(single)
    for directory in list:
        shutil.rmtree(directory)
    for directory in container_tmpdirs:
        shutil.rmtree(directory)
    return None


schedule = IntervalSchedule(interval=datetime.timedelta(minutes=1))

with Flow(
    "CRIS Crash Import",
    # schedule=Schedule(clocks=[CronClock("* * * * *")]),
    run_config=UniversalRun(labels=["vision-zero", "atd-data03"]),
) as flow:

    # repo = pull_from_github()
    # zip_location = download_extract_archives(repo)

    # get a location on disk which contains the zips from the sftp endpoint
    zip_location = download_extract_archives()

    # iterate over the zips in that location and unarchive them into
    # a list of temporary directories containtain the files of each
    extracts = unzip_archives(zip_location)

    # make sure we have the docker image we want to use to process these built.
    # NB: the extracts argument is thrown away. it's here to serialize the process
    image = build_docker_image(extracts)

    # Prefect is deep-magic. ✨
      # This array becomes first-class task, as it's an interable that
      # controls flow by accumulating return values from other tasks.
      # Think of it like a Promise.all().
    container_tmpdirs = [] 
    for extract in extracts:
        for table in ["crash", "unit", "person", "primaryperson", "charges"]:
            # spin up the VZ ETL processor, per set of zips, per object type
            container_tmpdir = run_docker_image( # ← @task
                extract, image, ["/app/process_hasura_import.py", table]
            )
            container_tmpdirs.append(container_tmpdir)

    # remove all these workspaces we've made
    cleanup_temporary_directories(zip_location, extracts, container_tmpdirs)

# result = is_serializable(flow)
# print("Is Serializable:", result)

flow.register(project_name="vision-zero")
#flow.run()
