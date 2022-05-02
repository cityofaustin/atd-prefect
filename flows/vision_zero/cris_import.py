import os
import sys
from prefect import task, Flow
import sysrsync
import tempfile
import time
import pprint
import shutil
import docker

from colorama import init, Fore, Style
init()

SFTP_ENDPOINT = os.getenv('SFTP_ENDPOINT')
ZIP_PASSWORD = os.getenv('ZIP_PASSWORD')

pp = pprint.PrettyPrinter(indent=2)

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

def unzip_archives(archives_directory):
  print(Fore.GREEN + sys._getframe(  ).f_code.co_name + "()", Style.RESET_ALL)
  extracted_csv_directories = []
  for filename in os.listdir(archives_directory):
    print("File:", filename)
    #with tempfile.TemporaryDirectory() as extract_tmpdir:
    extract_tmpdir = tempfile.mkdtemp()
    unzip_command = f'7za -y -p{ZIP_PASSWORD} -o"{extract_tmpdir}" x "{archives_directory}/{filename}"'
    os.system(unzip_command)
    extracted_csv_directories.append(extract_tmpdir)
  return(extracted_csv_directories)

def docker():
  print(Fore.GREEN + sys._getframe(  ).f_code.co_name + "()", Style.RESET_ALL)
  #client = docker.from_env()


def cleanup_temporary_directories(single, list):
  print(Fore.GREEN + sys._getframe(  ).f_code.co_name + "()", Style.RESET_ALL)
  shutil.rmtree(single)
  for directory in list:
    shutil.rmtree(directory)


with Flow("VZ Ingest") as f:
  zip_location = download_extract_archives()
  extracts = unzip_archives(zip_location)
  cleanup_temporary_directories(zip_location, extracts)
  docker()

f.run()
