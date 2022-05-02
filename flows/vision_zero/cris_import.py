import os
import sys
import json
from prefect import task, Flow
import sysrsync
import tempfile
import time
import pprint
import shutil
import docker

from colorama import init, Fore, Style
init()

docker_client = docker.from_env()

SFTP_ENDPOINT = os.getenv('SFTP_ENDPOINT')
ZIP_PASSWORD = os.getenv('ZIP_PASSWORD')
RAW_AIRFLOW_CONFIG_JSON = os.getenv('RAW_AIRFLOW_CONFIG')
RAW_AIRFLOW_CONFIG = json.loads(RAW_AIRFLOW_CONFIG_JSON)


pp = pprint.PrettyPrinter(indent=2)


@task
def download_extract_archives():
  print(Fore.GREEN + sys._getframe(  ).f_code.co_name + "()", Style.RESET_ALL)
  zip_tmpdir = tempfile.mkdtemp()
  sysrsync.run(
    verbose=True,
    options=['-a'],
    source_ssh=SFTP_ENDPOINT,
    source='/home/txdot/*zip',
    sync_source_contents=False,
    destination=zip_tmpdir
    )
  print("Temp Directory:", zip_tmpdir)
  return(zip_tmpdir)


@task(nout=1)
def unzip_archives(archives_directory):
  print(Fore.GREEN + sys._getframe(  ).f_code.co_name + "()", Style.RESET_ALL)
  extracted_csv_directories = []
  for filename in os.listdir(archives_directory):
    print("File:", filename)
    extract_tmpdir = tempfile.mkdtemp()
    unzip_command = f'7za -y -p{ZIP_PASSWORD} -o"{extract_tmpdir}" x "{archives_directory}/{filename}"'
    os.system(unzip_command)
    extracted_csv_directories.append(extract_tmpdir)
  return(extracted_csv_directories)


@task
def build_docker_image(extracts):
  print(Fore.GREEN + sys._getframe(  ).f_code.co_name + "()", Style.RESET_ALL)
  build_result = docker_client.images.build(
    path="./atd-vz-data/atd-etl",
    tag="vz-etl"
  )
  return build_result[0]

@task
def run_docker_image(extracted_data, vz_etl_image, command):
  print(Fore.GREEN + sys._getframe(  ).f_code.co_name + "()", Style.RESET_ALL)
  
  docker_tmpdir = tempfile.mkdtemp()
  volumes = {
    docker_tmpdir: {'bind': '/app/tmp', 'mode': 'rw'},
    extracted_data: {'bind': '/data', 'mode': 'rw'}
    }

  log = docker_client.containers.run(
    image=vz_etl_image,
    command=command,
    volumes=volumes,
    remove=True,
    environment=RAW_AIRFLOW_CONFIG
    )
  print(log)
  return docker_tmpdir

@task
def cleanup_temporary_directories(single, list, container_tmpdirs):
  print(Fore.GREEN + sys._getframe(  ).f_code.co_name + "()", Style.RESET_ALL)
  shutil.rmtree(single)
  for directory in list:
    shutil.rmtree(directory)
  for directory in container_tmpdirs:
    shutil.rmtree(directory)
  return None


with Flow("Vision Zero Crash Ingest") as flow:
  zip_location = download_extract_archives()
  extracts = unzip_archives(zip_location)
  image = build_docker_image(extracts)
  container_tmpdirs = []
  for extract in extracts:
    for table in ['crash', 'unit', 'person', 'primaryperson', 'charges']:
      container_tmpdir = run_docker_image(extract, image, ['/app/process_hasura_import.py', table])
      container_tmpdirs.append(container_tmpdir)
  cleanup_temporary_directories(zip_location, extracts, container_tmpdirs)

flow.run()
