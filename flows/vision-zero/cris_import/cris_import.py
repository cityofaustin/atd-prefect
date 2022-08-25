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

import lib.mappings as mappings
import lib.sql as util

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


@task(name="Futter CSV into DB")
def futter_csvs_into_database(directory):

    """
    Use `pgfutter` to import each CSV file received from CRIS into the database. These tables created
    are found in the `import` schema, which can be configured via KV store or environment variable.
    The tables are DROPed and CREATED before each import, and the names used for each table are drawn
    from the filename provided by CRIS, extracted by a regex.

    Arguments:
        directory: String representing the path of the temporary directory containing the CSV files

    Returns: Boolean, as a prefect task token representing the import
    """

    # The program is distributed from GitHub compiled for multiple architectures. This utility checks the system
    # running the task and uses the correct one.
    futter = util.get_pgfutter_path()

    # print(f"Futtering: {directory}")

    # Walk the directory and find all the CSV files
    for root, dirs, files in os.walk(directory):
        for filename in files:
            if filename.endswith(".csv"):

                # Extract the table name from the filename. They are named `crash`, `unit`, `person`, `primaryperson`, & `charges`.
                table = re.search("extract_[\d_]+(.*)_[\d].*\.csv", filename).group(1)

                # Request the database drop any existing table with the same name
                cmd = f'echo "drop table {DB_IMPORT_SCHEMA}.{table};" | PGPASSWORD={DB_PASS} psql -h {DB_HOST} -U {DB_USER} {DB_NAME}'
                os.system(cmd)

                # Build the futter command with correct credentials
                cmd = (
                    f"{futter} --host {DB_HOST} --username {DB_USER} --pw {DB_PASS} --dbname {DB_NAME} --schema {DB_IMPORT_SCHEMA} --table "
                    + table
                    + " csv "
                    + directory
                    + "/"
                    + filename
                )
                # execute the futter command
                os.system(cmd)

    # return a token for prefect to hand off to subsequent tasks in the Flow
    return True

@task(name="Remove trailing carriage returns from imported data")
def remove_trailing_carriage_returns(futter_token):

    pg = psycopg2.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, dbname=DB_NAME)

    columns = util.get_input_tables_and_columns(pg, DB_IMPORT_SCHEMA)
    for column in columns:
        util.trim_trailing_carriage_returns(pg, DB_IMPORT_SCHEMA, column)



@task(name="Align DB Types")
def align_db_typing(trimmed_token):

    """
    This function compares the target table in the VZDB with the corollary table in the import schema. For each column pair,
    the type of the VZDB table's column is applied to the import table. This acts as a strong typing check for all input data,
    and will raise an exception if CRIS begins feeding the system data it's not ready to parse and handle.

    Arguments:
        futter_token: Boolean value received from the previously ran task which imported the CSV files into the database.

    Returns: Boolean representing the completion of the import table type alignment
    """

    # fmt: off
    # Note about the above comment. It's used to disable black linting. For this particular task, 
    # I believe it's more readable to not have it wrap long lists of function arguments. 


    pg = psycopg2.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, dbname=DB_NAME)

    # query list of the tables which were created by the pgfutter import process
    imported_tables = util.get_imported_tables(pg, DB_IMPORT_SCHEMA)

    # pull our map which connects the names of imported tables to the target tables in VZDB
    table_mappings = mappings.get_table_map()

    # iterate over table list to make sure we only are operating on the tables we've designated:
    # crash, unit, person, & primaryperson
    for input_table in imported_tables:
        output_table = table_mappings.get(input_table["table_name"])
        if not output_table:
            continue

        # Safety check to make sure that all incoming data has each row complete with a value in each of the "key" columns. Key columns are
        # the columns which are used to uniquely identify the entity being represented by a record in the database. 
        util.enforce_complete_keying(pg, mappings.get_key_columns(), output_table, DB_IMPORT_SCHEMA, input_table)

        # collect the column types for the target table, to be applied to the imported table
        output_column_types = util.get_output_column_types(pg, output_table)

        # iterate on each column
        for column in output_column_types:
            # for that column, confirm that it is included in the incoming CRIS data
            input_column_type = util.get_input_column_type(pg, DB_IMPORT_SCHEMA, input_table, column)

            # skip columns which do not appear in the import data, such as the columns we have added ourselves to the VZDB
            if not input_column_type:
                continue

            # form an ALTER statement to apply the type to the imported table's column
            alter_statement = util.form_alter_statement_to_apply_column_typing(DB_IMPORT_SCHEMA, input_table, column)
            print(f"Aligning types for {DB_IMPORT_SCHEMA}.{input_table['table_name']}.{column['column_name']}.")

            # and execute the statement
            cursor = pg.cursor()
            cursor.execute(alter_statement)
            pg.commit()

    # fmt: on
    return True


@task(name="Insert / Update records in target schema")
def align_records(typed_token, dry_run):

    """
    This function begins by preparing a number of list and string variables containing SQL fragments.
    These fragments are used to create queries which inspect the data differences between a pair of records.
    How the records differ, if at all, is used to create either an UPDATE or INSERT statement that keeps the VZDB
    up to date, including via backfill, from CRIS data.

    Additionally, this function demonstrates the ability to query a list of fields which are different for reporting
    and logging purposes.

    Arguments:
        typed_token: Boolean value received from task which aligned data types.

    Returns: Boolean representing the completion of the import / update
    """
    logger = prefect.context.get("logger")

    # fmt: off
    pg = psycopg2.connect(host=DB_HOST, user=DB_USER, password=DB_PASS, dbname=DB_NAME)
    print("Finding updated records")

    output_map = mappings.get_table_map()
    table_keys = mappings.get_key_columns()

    for table in output_map.keys():

        # Query the list of columns in the target table
        target_columns = util.get_target_columns(pg, output_map, table)

        # Get the list of columns which are designated to to be protected from updates
        no_override_columns = mappings.no_override_columns()[output_map[table]]

        # Load up the list of imported records to iterate over. 
        imported_records = util.load_input_data_for_keying(pg, DB_IMPORT_SCHEMA, table)

        # Get columns used to uniquely identify a record
        key_columns = mappings.get_key_columns()[output_map[table]]

        # Build SQL fragment used as a JOIN ON clause to link input and output tables
        linkage_clauses, linkage_sql = util.get_linkage_constructions(key_columns, output_map, table, DB_IMPORT_SCHEMA)

        # Build list of columns available for import by inspecting the input table
        input_column_names = util.get_input_column_names(pg, DB_IMPORT_SCHEMA, table, target_columns)

        # iterate over each imported record and determine correct action
        for source in imported_records:

            # generate some record specific SQL fragments to identify the record in larger queries
            public_key_sql, import_key_sql = util.get_key_clauses(table_keys, output_map, table, source, DB_IMPORT_SCHEMA)

            # To decide to UPDATE, we need to find a matching target record in the output table.
            # This function returns that record as a token of existence or false if none is available
            if util.fetch_target_record(pg, output_map, table, public_key_sql):
                # Build 3 arrays of SQL fragments, one element per column which can be `join`ed together in subsequent queries.
                column_assignments, column_comparisons, column_aggregators = util.get_column_operators(target_columns, no_override_columns, source, table, output_map, DB_IMPORT_SCHEMA)

                # Check if the proposed update would result in a non-op, such as if there are no changes between the import and
                # target record. If this is the case, continue to the next record. There's no changes needed in this case.
                if util.check_if_update_is_a_non_op(pg, column_comparisons, output_map, table, linkage_clauses, public_key_sql, DB_IMPORT_SCHEMA):
                    #logger.info(f"Skipping update for {output_map[table]} {public_key_sql}")
                    continue


                # For future reporting and debugging purposes: Use SQL to query a list of 
                # column names which have differing values between the import and target records.
                # Return these column names as an array and display them in the output.
                changed_columns = util.get_changed_columns(pg, column_aggregators, output_map, table, linkage_clauses, public_key_sql, DB_IMPORT_SCHEMA)

                #print("Changed Columns:" + str(changed_columns["changed_columns"]))

                # Display the before and after values of the columns which are subject to update
                util.show_changed_values(pg, changed_columns, output_map, table, linkage_clauses, public_key_sql, DB_IMPORT_SCHEMA)

                # Using all the information we've gathered, form a single SQL update statement to update the target record.
                update_statement = util.form_update_statement(output_map, table, column_assignments, DB_IMPORT_SCHEMA, public_key_sql, linkage_sql, changed_columns)
                logger.info(f"Executing update in {output_map[table]} for where " + public_key_sql)

                # Execute the update statement
                util.try_statement(pg, output_map, table, public_key_sql, update_statement, dry_run)
                if len(changed_columns["changed_columns"]) == 0:
                    logger.info(update_statement)
                    raise "No changed columns? Why are we forming an update? This is a bug."

            # target does not exist, we're going to insert
            else:
                # An insert is always just an vanilla insert, as there is not a pair of records to compare.
                # Produce the SQL which creates a new VZDB record from a query of the imported data
                insert_statement = util.form_insert_statement(output_map, table, input_column_names, import_key_sql, DB_IMPORT_SCHEMA)
                logger.info(f"Executing insert in {output_map[table]} for where " + public_key_sql)

                # Execute the insert statement
                util.try_statement(pg, output_map, table, public_key_sql, insert_statement, dry_run)

    # fmt: on
    return True


with Flow(
    "CRIS Crash Import",
    # state_handlers=[skip_if_running_handler],
) as flow:

    dry_run = True

    # get a location on disk which contains the zips from the sftp endpoint
    # zip_location = download_extract_archives()

    # OR

    zip_location = specify_extract_location(
        # "/root/cris_import/data/2022-ytd.zip",
        "/root/cris_import/data/july-2022.zip",
    )

    # iterate over the zips in that location and unarchive them into
    # a list of temporary directories containing the files of each
    extracted_archives = unzip_archives(zip_location)

    futter_token = futter_csvs_into_database.map(extracted_archives)

    trimmed_token = remove_trailing_carriage_returns(futter_token)

    typed_token = align_db_typing(trimmed_token=trimmed_token)

    align_records(typed_token=typed_token, dry_run=dry_run)

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
#flow.register(project_name="vision-zero")
flow.run()
