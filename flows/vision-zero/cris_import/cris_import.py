#!/usr/bin/python3

import os
import sys
import json
import shutil
import time
import datetime
import tempfile
from subprocess import Popen, PIPE

import boto3
import docker
import sysrsync
from git import Repo

# Import various prefect packages and helper methods
import prefect
from prefect import task, Flow, unmapped
from prefect.client import Client
from prefect.engine.state import Skipped
from prefect.backend import get_key_value
from prefect.schedules import Schedule
from prefect.schedules.clocks import CronClock
from prefect.run_configs import UniversalRun

kv_store = get_key_value('Vision Zero Development')
kv_dictionary = json.loads(kv_store)

SFTP_ENDPOINT = kv_dictionary["SFTP_ENDPOINT"]
ZIP_PASSWORD = kv_dictionary["ZIP_PASSWORD"]
VZ_ETL_LOCATION = kv_dictionary["VZ_ETL_LOCATION"]

RAW_AIRFLOW_CONFIG_JSON = kv_dictionary["RAW_AIRFLOW_CONFIG"]
RAW_AIRFLOW_CONFIG = json.loads(RAW_AIRFLOW_CONFIG_JSON)

AWS_DEFAULT_REGION = kv_dictionary["AWS_DEFAULT_REGION"]
AWS_ACCESS_KEY_ID = kv_dictionary["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = kv_dictionary["AWS_SECRET_ACCESS_KEY"]
AWS_CSV_ARCHIVE_BUCKET_NAME = kv_dictionary["AWS_CSV_ARCHIVE_BUCKET_NAME"]
AWS_CSV_ARCHIVE_PATH_PRODUCTION = kv_dictionary["AWS_CSV_ARCHIVE_PATH_PRODUCTION"]
AWS_CSV_ARCHIVE_PATH_STAGING = kv_dictionary["AWS_CSV_ARCHIVE_PATH_STAGING"]

def skip_if_running_handler(obj, old_state, new_state):
    """
    State management function to prevent a flow executing if it's already running

    See: https://github.com/PrefectHQ/prefect/discussions/5373#discussioncomment-2054536
    """

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


@task(
    name="Download archive from SFTP Endpoint",
    slug="get-zips",
    max_retries=3,
    retry_delay=datetime.timedelta(minutes=2),
)
def download_extract_archives():
    """
    Connect to the SFTP endpoint which receives archives from CRIS and 
    download them into a temporary directory.

    Returns path of temporary directory as a string
    """

    logger = prefect.context.get("logger")
    logger.info(sys._getframe().f_code.co_name + "()")
    zip_tmpdir = tempfile.mkdtemp()
    rsync = sysrsync.run(
        verbose=True,
        options=["-a"],
        source_ssh=SFTP_ENDPOINT,
        source="/home/txdot/*zip",
        sync_source_contents=False,
        destination=zip_tmpdir,
    )
    logger.info("Rsync return code: " + str(rsync.returncode))
    if (rsync.returncode != 0):
        return false
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
    """
    Unzips (and decrypts) archives received from CRIS

    Arguments: A path to a directory containing archives as a string

    Returns: A list of strings, each denoting a path to a folder
    containing an archive's contents
    """
    
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
def build_docker_image():
    """
    Builds (or updates) the VZ ETL. 
    Almost always, this will be a non-op and return almost instantly.

    Returns: Docker object representing the built image; used later to start a containr
    """
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
    """
    Execute the VZ ETL Tool which runs in a docker container. 

    Arguments: 
        extracted_data: A string denoting a path of a folder containing an unarchived extract
        vz_etl_image: A docker object referencing an image to run
        command: The particular command that will be used as the container entrypoint
    """
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
        command=command,
        volumes=volumes,
        network_mode="host",  # This should be doable in bridged network mode. TODO: Investigate
        remove=True,
        environment=RAW_AIRFLOW_CONFIG,
    )
    
    return docker_tmpdir


@task(name="Cleanup temporary directories", slug="cleanup-temporary-directories")
def cleanup_temporary_directories(zip_location, extracted_archives, crash_import_tmpdirs, unit_import_tmpdirs, person_import_tmpdirs, primaryperson_import_tmpdirs, charges_import_tmpdirs):
    """
    Remove directories that have accumulated during the flow's execution

    Arguments:
        zip_location: A string containing a path to a temporary directory
        extracted_archives: A list of strings each containing a path to a temporary directory
        crash_import_tmpdirs: A list of strings each containing a path to a temporary directory
        unit_import_tmpdirs: A list of strings each containing a path to a temporary directory
        person_import_tmpdirs: A list of strings each containing a path to a temporary directory
        primaryperson_import_tmpdirs: A list of strings each containing a path to a temporary directory
        charges_import_tmpdirs: A list of strings each containing a path to a temporary directory

    Returns: None
    """

    logger = prefect.context.get("logger")
    logger.info(sys._getframe().f_code.co_name + "()")

    shutil.rmtree(zip_location)
    for directory in extracted_archives:
        shutil.rmtree(directory)
    for directory in crash_import_tmpdirs:
        shutil.rmtree(directory)
    for directory in unit_import_tmpdirs:
        shutil.rmtree(directory)
    for directory in person_import_tmpdirs:
        shutil.rmtree(directory)
    for directory in primaryperson_import_tmpdirs:
        shutil.rmtree(directory)
    for directory in charges_import_tmpdirs:
        shutil.rmtree(directory)

    return None

@task(name="Upload CSV files on s3 for archival")
def upload_csv_files_to_s3(extract_directory):
    """
    Upload CSV files which came from CRIS exports up to S3 for archival

    Arguments:
        extract_directory: String denoting the full path of a directory containing extracted CSV files

    Returns:
        extract_directory: String denoting the full path of a directory containing extracted CSV files
            NB: The in-and-out unchanged data in this function is more about serializing prefect tasks and less about inter-functional communication
    """
    logger = prefect.context.get("logger")
    logger.info(sys._getframe().f_code.co_name + "()")
    
    session = boto3.Session(
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        )
    s3 = session.resource('s3')

    #for extract_directory in extracts:
    for filename in os.listdir(extract_directory):
        logger.info("About to upload to s3: " + filename)
        destination_path = AWS_CSV_ARCHIVE_PATH_STAGING + '/' + str(datetime.date.today())
        s3.Bucket(AWS_CSV_ARCHIVE_BUCKET_NAME).upload_file(
            extract_directory + '/' + filename,
            destination_path  + '/' + filename,
            )
    return extract_directory

@task(name="Remove archive from SFTP Endpoint")
def remove_archives_from_sftp_endpoint(zip_location):
    """
    Delete the archives which have been processed from the SFTP endpoint

    Arguments:
        zip_location: Stringing containing path of a directory containing the zip files downloaded from SFTP endpoint

    Returns: None
    """
    logger = prefect.context.get("logger")
    logger.info(sys._getframe().f_code.co_name + "()")
    logger.info(zip_location)
    for archive in os.listdir(zip_location):
        logger.info(archive)
        command = f'ssh {SFTP_ENDPOINT} rm -v /home/txdot/{archive}'
        logger.info(command)
        cmd = command.split()
        rm_result = Popen(cmd, stdout=PIPE, stderr=PIPE, stdin=PIPE).stdout.read()
        logger.info(rm_result)

    return None


with Flow(
    "CRIS Crash Import",
    # schedule=Schedule(clocks=[CronClock("* * * * *")]),
    run_config=UniversalRun(labels=["vision-zero", "atd-data03"]),
    state_handlers=[skip_if_running_handler],
) as flow:
    # make sure we have the docker image we want to use to process these built.
    image = build_docker_image()

    # get a location on disk which contains the zips from the sftp endpoint
    zip_location = download_extract_archives()

    # iterate over the zips in that location and unarchive them into
    # a list of temporary directories containtain the files of each
    extracted_archives = unzip_archives(zip_location)

    # push up the archives to s3 for archival
    uploaded_archives_csvs = upload_csv_files_to_s3.map(extracted_archives)

    #def run_docker_image(extracted_data, vz_etl_image, command):
    crash_import_tmpdirs = run_docker_image.map(extracted_data=uploaded_archives_csvs, vz_etl_image=unmapped(image), command=unmapped(["/app/process_hasura_import.py", "crash"]))

    # the next four set of task calls; i want them to be in parallel, but this won't work without a dask setup, i think
    unit_import_tmpdirs = run_docker_image.map(extracted_data=uploaded_archives_csvs, vz_etl_image=unmapped(image), command=unmapped(["/app/process_hasura_import.py", "unit"]))
    unit_import_tmpdirs.set_upstream(crash_import_tmpdirs)

    person_import_tmpdirs = run_docker_image.map(extracted_data=uploaded_archives_csvs, vz_etl_image=unmapped(image), command=unmapped(["/app/process_hasura_import.py", "person"]))
    person_import_tmpdirs.set_upstream(crash_import_tmpdirs)

    primaryperson_import_tmpdirs = run_docker_image.map(extracted_data=uploaded_archives_csvs, vz_etl_image=unmapped(image), command=unmapped(["/app/process_hasura_import.py", "primaryperson"]))
    primaryperson_import_tmpdirs.set_upstream(crash_import_tmpdirs)

    charges_import_tmpdirs = run_docker_image.map(extracted_data=uploaded_archives_csvs, vz_etl_image=unmapped(image), command=unmapped(["/app/process_hasura_import.py", "charges"]))
    charges_import_tmpdirs.set_upstream(crash_import_tmpdirs)
    
    # remove archives from SFTP endpoint
    removal_token = remove_archives_from_sftp_endpoint(zip_location)
    removal_token.set_upstream(crash_import_tmpdirs)
    removal_token.set_upstream(unit_import_tmpdirs)
    removal_token.set_upstream(person_import_tmpdirs)
    removal_token.set_upstream(primaryperson_import_tmpdirs)
    removal_token.set_upstream(charges_import_tmpdirs)

    cleanup = cleanup_temporary_directories(zip_location, extracted_archives, crash_import_tmpdirs, unit_import_tmpdirs, person_import_tmpdirs, primaryperson_import_tmpdirs, charges_import_tmpdirs)
    cleanup.set_upstream(removal_token)

# I'm not sure how to make this not self-label by the hostname of the registering computer.
# here, it only tags it with the docker container ID, so no harm, no foul, but it's noisy.
flow.register(project_name="vision-zero")
#flow.run()
