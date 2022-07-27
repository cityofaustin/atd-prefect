# Standard Library imports
from io import StringIO
import os
import platform

# Related third party imports
from prefect import task, Flow, Parameter, unmapped
from prefect.schedules import IntervalSchedule
from prefect.run_configs import UniversalRun, DockerRun
from prefect.backend import set_key_value, get_key_value
from prefect.storage import Docker, GitHub

from mstrio.connection import Connection
from mstrio.project_objects import Report

import boto3
import pandas as pd

hostname = platform.node()



# Microstrategy Credentials
PROJECT_ID = "6B64D80C11E1AFEA001000805B2705A0"
BASE_URL = "https://mstrprod-library.austintexas.gov/MicroStrategyLibrary/api/"

environment_variables = get_key_value(key=f"atd_microstrategy")

MSTRO_USERNAME = environment_variables["MSTRO_USERNAME"]
MSTRO_PASSWORD = environment_variables["MSTRO_PASSWORD"]

# 2D array where each row is a report to be retrived
## [File Name for S3, Report ID]
# To find report ID, go to the report in Microstrategy then:
## Go to Tools > Report Details Page or Document Details Page.
## Click Show Advanced Details button at the bottom
# REPORTS = [
#     ["2020 Bond Expenses Obligated", "85A9E0A049F06D98AF1CF3BE8CDA9394"],
#     ["All Bonds Expenses Obligated", "aaabb"],
# ]

REPORTS = [
    ["2020 Bond Expenses Obligated", "85A9E0A049F06D98AF1CF3BE8CDA9394"],
    # ["All Bonds Expenses Obligated", "aaabb"],
]

report_names = [i[0] for i in REPORTS]
report_ids = [i[1] for i in REPORTS]

## AWS Credentials
AWS_ACCESS_ID = environment_variables["AWS_ACCESS_ID"]
AWS_PASS = environment_variables["AWS_PASS"]
BUCKET_NAME = environment_variables["BUCKET"]


@task
def connect_to_mstro():
    conn = Connection(
        base_url=BASE_URL,
        username=MSTRO_USERNAME,
        password=MSTRO_PASSWORD,
        project_id=PROJECT_ID,
        login_mode=1,
    )
    return conn


@task
def connect_to_AWS():


    session = boto3.Session(
        aws_access_key_id=AWS_ACCESS_ID, aws_secret_access_key=AWS_PASS,
    )
    s3_res = session.resource("s3")

    return s3_res


@task()
def download_report(report_id, conn):


    my_report = Report(connection=conn, id=report_id, parallel=False)
    my_report_df = my_report.to_dataframe()
    return my_report_df


@task
def report_to_s3(df, report_name, s3):


    csv_buffer = StringIO()
    df.to_csv(csv_buffer, index=False)
    file_name = f"{report_name}.csv"
    s3.Object(BUCKET_NAME, file_name).put(Body=csv_buffer.getvalue())


with Flow( f"MicroStrategy to S3", run_config=UniversalRun(labels=["microstrategy", hostname])) as flow:

    ids = Parameter("report_ids", default=report_ids, required=True)

    names = Parameter("report_names", default=report_names, required=True)
    flow.add_task(names)

    conn = connect_to_mstro()
    s3 = connect_to_AWS()
    df = download_report.map(ids, unmapped(conn))
    report_to_s3.map(df, names, unmapped(s3))

#flow.run(parameters={"report_ids": report_ids, "report_names": report_names})
flow.register(project_name="Microstrategy")
