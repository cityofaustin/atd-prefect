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
from prefect import task, Flow
from prefect.schedules import Schedule
from prefect.schedules.clocks import CronClock
from prefect.run_configs import UniversalRun
from prefect.utilities.debug import is_serializable
from colorama import init, Fore, Style

init() # init colorama for ANSI color codes

docker_client = docker.from_env()

PWD = os.getenv("PWD")
SFTP_ENDPOINT = os.getenv("SFTP_ENDPOINT")
ZIP_PASSWORD = os.getenv("ZIP_PASSWORD")
RAW_AIRFLOW_CONFIG_JSON = os.getenv("RAW_AIRFLOW_CONFIG")
RAW_AIRFLOW_CONFIG = json.loads(RAW_AIRFLOW_CONFIG_JSON)


pp = pprint.PrettyPrinter(indent=2)


@task
def pull_from_github():
    print(Fore.GREEN + sys._getframe().f_code.co_name + "()", Style.RESET_ALL)
    repo = Repo(PWD)
    origin = repo.remotes[0]
    pull_result = origin.pull()

    # sms = repo.submodules
    # for sm in sms:
    # print(sm.remotes)

    return repo


@task
def download_extract_archives():
    print(Fore.GREEN + sys._getframe().f_code.co_name + "()", Style.RESET_ALL)
    zip_tmpdir = tempfile.mkdtemp()
    sysrsync.run(
        verbose=True,
        options=["-a"],
        source_ssh=SFTP_ENDPOINT,
        source="/home/txdot/*zip",
        sync_source_contents=False,
        destination=zip_tmpdir,
    )
    print("Temp Directory:", zip_tmpdir)
    return zip_tmpdir


@task(nout=1)
def unzip_archives(archives_directory):
    print(Fore.GREEN + sys._getframe().f_code.co_name + "()", Style.RESET_ALL)
    extracted_csv_directories = []
    for filename in os.listdir(archives_directory):
        print("File:", filename)
        extract_tmpdir = tempfile.mkdtemp()
        unzip_command = f'7za -y -p{ZIP_PASSWORD} -o"{extract_tmpdir}" x "{archives_directory}/{filename}"'
        os.system(unzip_command)
        extracted_csv_directories.append(extract_tmpdir)
    return extracted_csv_directories


@task
def build_docker_image(extracts):
    print(Fore.GREEN + sys._getframe().f_code.co_name + "()", Style.RESET_ALL)
    build_result = docker_client.images.build(
        path="./atd-vz-data/atd-etl", tag="vz-etl"
    )
    return build_result[0]


@task
def run_docker_image(extracted_data, vz_etl_image, command):
    print(Fore.GREEN + sys._getframe().f_code.co_name + "()", Style.RESET_ALL)

    docker_tmpdir = tempfile.mkdtemp()
    #return docker_tmpdir  # this is short circuiting out the rest of this routine (for speed of dev)
    volumes = {
        docker_tmpdir: {"bind": "/app/tmp", "mode": "rw"},
        extracted_data: {"bind": "/data", "mode": "rw"},
    }

    log = docker_client.containers.run(
        image=vz_etl_image,
        name="vz_etl",
        command=command,
        volumes=volumes,
        network_mode="host",  # This should be doable in bridged network mode. TODO: Investigate
        remove=True,
        environment=RAW_AIRFLOW_CONFIG,
    )
    print(log)
    return docker_tmpdir


@task
def cleanup_temporary_directories(single, list, container_tmpdirs):
    print(Fore.GREEN + sys._getframe().f_code.co_name + "()", Style.RESET_ALL)
    shutil.rmtree(single)
    for directory in list:
        shutil.rmtree(directory)
    for directory in container_tmpdirs:
        shutil.rmtree(directory)
    return None


project_name = "Vision Zero Crash Import"

with Flow(
    project_name,
    #schedule=Schedule(clocks=[CronClock("* * * * *")]),
    #run_config=UniversalRun(labels=["vision-zero", "atd-data03"]),
) as flow:

    # repo = pull_from_github()
    # zip_location = download_extract_archives(repo)

    zip_location = download_extract_archives()
    extracts = unzip_archives(zip_location)
    image = build_docker_image(extracts)
    container_tmpdirs = []
    for extract in extracts:
        for table in ["crash", "unit", "person", "primaryperson", "charges"]:
            # this construct is useful to have the docker image spin while you run a process manually
            # container_tmpdir = run_docker_image(extract, image, ['sleep', '3000'])
            container_tmpdir = run_docker_image(
                extract, image, ["/app/process_hasura_import.py", table]
            )
            container_tmpdirs.append(container_tmpdir)
    cleanup_temporary_directories(zip_location, extracts, container_tmpdirs)

result = is_serializable(flow)
print(result)

# flow.register(project_name=project_name)
flow.run()
