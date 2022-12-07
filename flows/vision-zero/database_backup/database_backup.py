import os
from datetime import datetime
import docker
from dotenv import load_dotenv, find_dotenv
from pathlib import Path

load_dotenv()

env_path = Path('.')/'postgresql.env'
print(env_path)
load_dotenv(dotenv_path=env_path)

PGPASSWORD = os.getenv("PGPASSWORD")

def get_current_datetime():
  current_datetime = datetime.now()
  date = current_datetime.strftime("%Y-%m-%d")
  time = current_datetime.strftime("%H-%M")
  print("Making backup for",  date, "at", time)
  return date, time

def make_backup_directory(date):
  path = ("./tmp/" + date)
  os.makedirs(path, exist_ok=True)

def get_backup():
  response = (
    docker.from_env()
    .containers.run(
      image="postgres:14-bullseye",
      command="pg_dump -U vze -h db-rr.vision-zero.austinmobility.io --format=custom atd_vz_data",
      remove=True,
      environment=[PGPASSWORD],
      stdin_open=True,
      tty=True,
      stdout=True,
      stream=True,
    )
  )
  print(response)
  return response

def get_aws_credentials():
  response = (
    docker.from_env()
    .containers.run(
      image="amazon/aws-cli",
      command=["s3", "sync", "/tmp/", "s3://atd-vision-zero-database/backups/atd_vz_data_production"],
      remove=True,
      volumes=["`pwd`/aws_credentials:/root/.aws", "`pwd`/tmp:/tmp"],
    )
  )
  return response

def remove_dir():
  os.removedirs("./tmp")

def main():
  date, time = get_current_datetime()
  make_backup_directory(date)
  get_backup()
  # get_aws_credentials()


if __name__ == "__main__":
    main()