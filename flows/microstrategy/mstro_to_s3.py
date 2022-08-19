# Standard Library imports
import datetime
from io import StringIO
import os

# Prefect imports
from prefect import task, Flow, Parameter, unmapped
from prefect.engine.state import Failed
from prefect.schedules import IntervalSchedule
from prefect.run_configs import UniversalRun, DockerRun
from prefect.backend import set_key_value, get_key_value
from prefect.storage import Docker, GitHub
from prefect.utilities.notifications import slack_notifier


# Related third party imports
import boto3
from mstrio.connection import Connection
from mstrio.project_objects import Report
import pandas as pd

handler = slack_notifier(only_states=[Failed])

environment_variables = get_key_value(key=f"atd_microstrategy")

ENV = "prod"

# Microstrategy Credentials
PROJECT_ID = "6B64D80C11E1AFEA001000805B2705A0"
BASE_URL = "https://mstrprod-library.austintexas.gov/MicroStrategyLibrary/api/"
MSTRO_USERNAME = environment_variables["MSTRO_USERNAME"]
MSTRO_PASSWORD = environment_variables["MSTRO_PASSWORD"]

# List dicts of default reports to be retrived
# To find report ID, go to the report in Microstrategy then:
## Go to Tools > Report Details Page or Document Details Page.
## Click Show Advanced Details button at the bottom
# Report name should be unique as it is the file name in the S3 bucket
REPORTS = [
    {"name": "2020 Bond Expenses Obligated", "id": "85A9E0A049F06D98AF1CF3BE8CDA9394"},
    {"name": "All bonds Expenses Obligated", "id": "6B0DE57644C7C9912AAAE48392873233"},
]

## AWS Credentials
AWS_ACCESS_ID = environment_variables["AWS_ACCESS_ID"]
AWS_PASS = environment_variables["AWS_PASS"]
BUCKET_NAME = environment_variables["BUCKET"]

# Report names and ids separated from dicts
report_names = [i["name"] for i in REPORTS]
report_ids = [i["id"] for i in REPORTS]

# Returns a connection object for interacting with the microstrategy API
@task(
    max_retries=2, retry_delay=datetime.timedelta(minutes=10), state_handlers=[handler],
)
def connect_to_mstro():
    conn = Connection(
        base_url=BASE_URL,
        username=MSTRO_USERNAME,
        password=MSTRO_PASSWORD,
        project_id=PROJECT_ID,
        login_mode=1,
    )
    return conn


# Returns a s3 object for interacting with the boto3 AWS S3 API
@task(
    max_retries=2, retry_delay=datetime.timedelta(minutes=10), state_handlers=[handler],
)
def connect_to_AWS():
    session = boto3.Session(
        aws_access_key_id=AWS_ACCESS_ID, aws_secret_access_key=AWS_PASS,
    )
    s3_res = session.resource("s3")

    return s3_res


# Downloads a report from microstrategy with a given report_id
# returns it as a pandas dataframe
@task(
    max_retries=3, retry_delay=datetime.timedelta(minutes=2),
)
def download_report(report_id, conn):
    my_report = Report(connection=conn, id=report_id, parallel=False)
    return my_report.to_dataframe()


# Takes a pandas dataframe and formats it to be sent as a .csv in an S3 bucket
# Uses the report_name.csv as a file name
# report_name should be unique or it'll overwrite another report
@task(
    max_retries=2, retry_delay=datetime.timedelta(minutes=10), state_handlers=[handler],
)
def report_to_s3(df, report_name, s3):
    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False)
    file_name = f"{report_name}.csv"
    s3.Object(BUCKET_NAME, file_name).put(Body=csv_buffer.getvalue())


# Define prefect flow
with Flow(
    f"microstrategy_to_s3_{ENV}",
    schedule=None,  # initalizing with no schedule
    # DockerRun needs a docker agent
    run_config=DockerRun(labels=[ENV, "docker", "atd-data03"]),
) as flow:
    # Mapping parameters
    ids = Parameter("report_ids", default=report_ids, required=True)
    names = Parameter("report_names", default=report_names, required=True)
    flow.add_task(names)

    # 1. Get microstrategy connection
    conn = connect_to_mstro()

    # 2. Connect using boto3 to our S3
    s3 = connect_to_AWS()

    # 3. Download report to df (for each report_id)
    df = download_report.map(ids, unmapped(conn))

    # 4. Send file to S3 bucket (for each report_id)
    report_to_s3.map(df, names, unmapped(s3))

flow.storage = Docker(
    registry_url="atddocker",
    image_name="atd-microstrategy",
    image_tag=ENV,
    python_dependencies=["mstrio-py", "pandas", "boto3"],
    # Can also/either include dockerfile = "path/to/Dockerfile" if you need to
    # better define your docker image.
)

# Defining default parameters for flow run
flow.run(parameters={"report_ids": report_ids, "report_names": report_names})
