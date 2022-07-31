#!/usr/bin/python3

import os
import json
import shutil
import re
import time
import datetime
import tempfile
from subprocess import Popen, PIPE

import boto3
import docker
import sysrsync
from git import Repo

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import psycopg2.extras

# Import various prefect packages and helper methods
import prefect
from prefect import task, Flow, unmapped
from prefect.client import Client
from prefect.engine.state import Skipped
from prefect.backend import get_key_value
from prefect.schedules import Schedule
from prefect.schedules.clocks import CronClock
from prefect.run_configs import UniversalRun

import lib.mappings as mappings

kv_store = get_key_value("Vision Zero")
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

DB_HOST = os.environ.get("DB_HOST")
DB_USER = os.environ.get("DB_USER")
DB_PASS = os.environ.get("DB_PASS")
DB_NAME = os.environ.get("DB_NAME")
DB_IMPORT_SCHEMA = os.environ.get("DB_IMPORT_SCHEMA")


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
            return Skipped(
                message
            )  # or returned Cancelled state if you prefer this state in this use case
    return new_state


@task(
    name="Specify where archive can be found",
    slug="locate-zips",
    max_retries=3,
    retry_delay=datetime.timedelta(minutes=2),
)
def specify_extract_location(file):
    zip_tmpdir = tempfile.mkdtemp()
    shutil.copy(file, zip_tmpdir)
    return zip_tmpdir


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
    # check for a OS level return code of anything non-zero, which
    # would indicate to us that the child proc we kicked off didn't
    # complete successfully.
    # see: https://www.gnu.org/software/libc/manual/html_node/Exit-Status.html
    if rsync.returncode != 0:
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
    extracted_csv_directories = []
    for filename in os.listdir(archives_directory):
        logger.info("About to unzip: " + filename + "with the command ...")
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
    docker_client = docker.from_env()
    build_result = docker_client.images.build(path=VZ_ETL_LOCATION, tag="vz-etl")
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

    docker_tmpdir = tempfile.mkdtemp()
    # return docker_tmpdir  # this is short circuiting out the rest of this routine (for speed of dev)
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
def cleanup_temporary_directories(
    zip_location,
    extracted_archives,
    crash_import_tmpdirs,
    unit_import_tmpdirs,
    person_import_tmpdirs,
    primaryperson_import_tmpdirs,
    charges_import_tmpdirs,
):
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

    session = boto3.Session(
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    )
    s3 = session.resource("s3")

    # for extract_directory in extracts:
    for filename in os.listdir(extract_directory):
        logger.info("About to upload to s3: " + filename)
        destination_path = (
            AWS_CSV_ARCHIVE_PATH_STAGING + "/" + str(datetime.date.today())
        )
        s3.Bucket(AWS_CSV_ARCHIVE_BUCKET_NAME).upload_file(
            extract_directory + "/" + filename,
            destination_path + "/" + filename,
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
    logger.info(zip_location)
    for archive in os.listdir(zip_location):
        logger.info(archive)
        command = f"ssh {SFTP_ENDPOINT} rm -v /home/txdot/{archive}"
        logger.info(command)
        cmd = command.split()
        rm_result = Popen(cmd, stdout=PIPE, stderr=PIPE, stdin=PIPE).stdout.read()
        logger.info(rm_result)

    return None


def get_pgfutter_path():
    uname = os.uname()
    print(uname.machine)
    if uname.machine == "aarch64":
        return "/root/pgfutter_arm"
    else:
        return "/root/pgfutter_x64"
    return None


@task(name="Futter CSV into DB")
def futter_csvs_into_database(directory):
    print("Futtering: " + directory)
    futter = get_pgfutter_path()
    for root, dirs, files in os.walk(directory):
        for filename in files:
            if filename.endswith(".csv"):
                table = re.search("extract_[\d_]+(.*)_[\d].*\.csv", filename).group(1)
                cmd = f'echo "drop table {DB_IMPORT_SCHEMA}.{table};" | PGPASSWORD={DB_PASS} psql -h {DB_HOST} -U {DB_USER} {DB_NAME}'
                os.system(cmd)
                cmd = (
                    f"{futter} --host {DB_HOST} --username {DB_USER} --pw {DB_PASS} --dbname {DB_NAME} --schema {DB_IMPORT_SCHEMA} --table "
                    + table
                    + " csv "
                    + directory
                    + "/"
                    + filename
                )
                os.system(cmd)


@task(name="Align DB Types")
def align_db_typing(futter_token):

    pg = psycopg2.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, dbname=DB_NAME)

    sql = "SELECT * FROM information_schema.tables WHERE table_schema = 'import';"
    cursor = pg.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cursor.execute(sql)
    imported_tables = cursor.fetchall()
    table_mappings = mappings.get_table_map()
    for input_table in imported_tables:
        output_table = table_mappings.get(input_table["table_name"])
        if not output_table:
            continue

        # This is a subtle SQL injection attack vector.
        # Beware the f-string. But I trust CRIS.
        sql = f"""
        SELECT
            column_name,
            data_type,
            character_maximum_length AS max_length,
            character_octet_length AS octet_length
        FROM
            information_schema.columns
        WHERE true
            AND table_schema = 'public'
            AND table_name = '{output_table}'
        """

        cursor = pg.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(sql)
        output_column_types = cursor.fetchall()

        for column in output_column_types:
            sql = f"""
            SELECT
                column_name,
                data_type,
                character_maximum_length AS max_length,
                character_octet_length AS octet_length
            FROM
                information_schema.columns
            WHERE true
                AND table_schema = 'import'
                AND table_name = '{input_table["table_name"]}'
                AND column_name = '{column["column_name"]}'
            """

            cursor = pg.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(sql)
            input_column_type = cursor.fetchall()

            # skip columns we don't have in our db...
            if not input_column_type:
                continue

            # the `USING` hackery is due to the reality of the CSV null vs "" confusion
            sql = f"""
            ALTER TABLE import.{input_table["table_name"]}
            ALTER COLUMN {column["column_name"]} SET DATA TYPE {column["data_type"]}
            USING case when {column["column_name"]} = \'\' then null else {column["column_name"]}::{column["data_type"]} end
            """

            cursor = pg.cursor()
            cursor.execute(sql)
            pg.commit()

    return True


@task(name="Find updated records")
def find_updated_records(typed_token):
    pg = psycopg2.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, dbname=DB_NAME)

    print("Finding updated records")

    output_map = mappings.get_table_map()
    input_tables = {v: k for k, v in output_map.items()}
    output_tables = list(output_map.values())

    table_keys = mappings.get_key_columns()

    for table in output_map.keys():
        # if not table == "crash":
        # continue
        sql = "select * from import." + table
        print(sql)

        cursor = pg.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cursor.execute(sql)
        imported_records = cursor.fetchall()

        # print(imported_records)
        for input in imported_records:

            sql = f"""
            select * 
            from public.{output_map[table]}
            where true
"""
            for key in table_keys[output_map[table]]:
                sql += f"                and {key} = {input[key]}\n"
            cursor = pg.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            cursor.execute(sql)
            target = cursor.fetchone()

            if target:
                print("Found an update possible?")
            else:
                print("This needs to be inserted")


with Flow(
    "CRIS Crash Import",
    run_config=UniversalRun(labels=["vision-zero", "atd-data03"]),
    # state_handlers=[skip_if_running_handler],
) as flow:

    # get a location on disk which contains the zips from the sftp endpoint
    # zip_location = download_extract_archives()

    # OR

    zip_location = specify_extract_location(
        "/root/cris_import/data/july_01-july-08.zip"
    )

    # iterate over the zips in that location and unarchive them into
    # a list of temporary directories containing the files of each
    extracted_archives = unzip_archives(zip_location)

    futter_token = futter_csvs_into_database.map(extracted_archives)

    typed_token = align_db_typing(futter_token=futter_token)

    find_updated_records(typed_token=typed_token)

    # push up the archives to s3 for archival
    # uploaded_archives_csvs = upload_csv_files_to_s3.map(extracted_archives)

    # remove archives from SFTP endpoint
    # removal_token = remove_archives_from_sftp_endpoint(zip_location)

    # cleanup = cleanup_temporary_directories(
    # zip_location,
    # extracted_archives,
    # )
    # cleanup.set_upstream(removal_token)

# I'm not sure how to make this not self-label by the hostname of the registering computer.
# here, it only tags it with the docker container ID, so no harm, no foul, but it's noisy.
# flow.register(project_name="vision-zero")
flow.run()
