#!/usr/bin/python3

import os
import sys
import json
import shutil
import pprint
import time
import datetime
import tempfile

import boto3
import docker
import sysrsync
from git import Repo
import prefect
from prefect import task, Flow
from prefect.schedules import Schedule
from prefect.schedules import IntervalSchedule
from prefect.backend.artifacts import create_markdown_artifact
from prefect.client import Client
from prefect.engine.state import Skipped
from prefect.schedules.clocks import CronClock

from prefect.run_configs import UniversalRun


PWD = os.getenv("PWD")
SFTP_ENDPOINT = os.getenv("SFTP_ENDPOINT")
ZIP_PASSWORD = os.getenv("ZIP_PASSWORD")
RAW_AIRFLOW_CONFIG_JSON = os.getenv("RAW_AIRFLOW_CONFIG")
VZ_ETL_LOCATION = os.getenv("VZ_ETL_LOCATION")
RAW_AIRFLOW_CONFIG = json.loads(RAW_AIRFLOW_CONFIG_JSON)

AWS_DEFAULT_REGION = os.getenv("AWS_DEFAULT_REGION")
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_CSV_ARCHIVE_BUCKET_NAME = os.getenv("AWS_CSV_ARCHIVE_BUCKET_NAME")
AWS_CSV_ARCHIVE_PATH_PRODUCTION = os.getenv("AWS_CSV_ARCHIVE_PATH_PRODUCTION")
AWS_CSV_ARCHIVE_PATH_STAGING = os.getenv("AWS_CSV_ARCHIVE_PATH_STAGING")

pp = pprint.PrettyPrinter(indent=2)

def skip_if_running_handler(obj, old_state, new_state):
    if new_state.is_running():
        client = Client()
        query = """
            query($flow_id: uuid) {
              flow_run(
                where: {_and: [{flow_id: {_eq: $flow_id}},
                {state: {_eq: "Running"}}]}
                limit: 1
                offset: 1
              ) {
                name
                state
                start_time
              }
            }
        """
        response = client.graphql(
            query=query, variables=dict(flow_id=prefect.context.flow_id)
        )
        active_flow_runs = response["data"]["flow_run"]
        if active_flow_runs:
            logger = prefect.context.get("logger")
            message = "Skipping this flow run since there are already some flow runs in progress"
            logger.info(message)
            return Skipped(message) # or returned Cancelled state if you prefer this state in this use case
    return new_state



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
        logger.info("About to unzip: " + filename + 'with the command ...')
        extract_tmpdir = tempfile.mkdtemp()
        unzip_command = f'7za -y -p{ZIP_PASSWORD} -o"{extract_tmpdir}" x "{archives_directory}/{filename}"'
        logger.info(unzip_command)
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
    #return docker_tmpdir  # this is short circuiting out the rest of this routine (for speed of dev)
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
    {log}
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

@task(name="Upload CSV files on s3 for archival")
def upload_csv_files_to_s3(extracts):
    logger = prefect.context.get("logger")
    logger.info(sys._getframe().f_code.co_name + "()")
    
    session = boto3.Session(
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        )
    s3 = session.resource('s3')

    for extract_directory in extracts:
        for filename in os.listdir(extract_directory):
            logger.info("About to upload to s3: " + filename)
            destination_path = AWS_CSV_ARCHIVE_PATH_STAGING + '/' + str(datetime.date.today())
            s3.Bucket(AWS_CSV_ARCHIVE_BUCKET_NAME).upload_file(
                extract_directory + '/' + filename,
                destination_path  + '/' + filename,
                )


schedule = IntervalSchedule(interval=datetime.timedelta(minutes=1))

with Flow(
    "CRIS Crash Import",
    # schedule=Schedule(clocks=[CronClock("* * * * *")]),
    run_config=UniversalRun(labels=["vision-zero", "atd-data03"]),
    state_handlers=[skip_if_running_handler],
) as flow:
    # repo = pull_from_github()
    # zip_location = download_extract_archives(repo)

    # get a location on disk which contains the zips from the sftp endpoint
    zip_location = download_extract_archives()

    # iterate over the zips in that location and unarchive them into
    # a list of temporary directories containtain the files of each
    extracts = unzip_archives(zip_location)

    # push up the archives to s3 for archival
    upload_csv_files_to_s3(extracts)

    # make sure we have the docker image we want to use to process these built.
    # NB: the extracts argument is thrown away. it's here to serialize the process
    image = build_docker_image(extracts)

    # Prefect is deep-magic. ✨
      # This array becomes a first-class task ("List"), as it's an interable that
      # controls flow by accumulating return values from other tasks.
      # Think of it like a Promise.all().
    container_tmpdirs = [] 

    # TODO: construct this that it runs "crash" first, and then the 
    # next four object types in parallel.
    for extract in extracts:
        for table in ["crash", "unit", "person", "primaryperson", "charges"]:
            # spin up the VZ ETL processor, per set of zips, per object type
            container_tmpdir = run_docker_image( # ← @task
                extract, image, ["/app/process_hasura_import.py", table]
            )
            container_tmpdirs.append(container_tmpdir)

    # remove all these workspaces we've made
    cleanup_temporary_directories(zip_location, extracts, container_tmpdirs)

# i'm not sure how to make this not self-label by the hostname of the registering computer.
# here, it only tags it with the docker container ID, so no harm, no foul, but it's noisy.
flow.register(project_name="vision-zero")
#flow.run()
