# Standard Library imports
import os
import pprint
import ntpath
from datetime import datetime

# Related third party imports
import boto3
import pandas
import mailparser
import email
import psycopg2
from psycopg2 import Error


pp = pprint.PrettyPrinter(indent=4)

# Environment variables
# TODO IF NEEDED
# BUCKET_NAME = os.environ.get("BUCKET_NAME")
# BUCKET_NAME = "atd-afd-incident-data"


def get_most_recent_file(bucket, client):
    """
    Find the most recently updated file in the bucket. This will be the newest email.
    Gets a string version of the Key representing the most recent S3 file.
    :param bucket: string key to bucket
    :param client: instance of S3 Client objects
    :return: string
    """

    # Stack Overflow helped:
    # https://stackoverflow.com/questions/45375999/how-to-download-the-latest-file-of-an-s3-bucket-using-boto3
    get_last_modified = lambda obj: int(obj["LastModified"].strftime("%s"))

    all_bucket_objects = client.list_objects_v2(Bucket=bucket)["Contents"]
    # only look in "atd-afd/" directory
    raw_emails_list = [obj for obj in all_bucket_objects if "atd-afd/" in obj["Key"]]
    # Newest Key as string
    last_added_key = [
        obj["Key"] for obj in sorted(raw_emails_list, key=get_last_modified)
    ][-1]

    pp.pprint(f"Downloading file from S3: {last_added_key}")

    # Get the newest item in the bucket
    # https://gist.github.com/sandeepmanchi/365bff15f2f395eeee45dd2d70e85e09
    newest_object = client.get_object(
        Bucket=bucket,
        Key=last_added_key,
    )

    return newest_object


def upload_data_to_postgres(data):
    try:
        connection = psycopg2.connect(
            user=DB_USERNAME,
            password=DB_PASSWORD,
            host=DB_HOSTNAME,
            port=DB_PORT,
            database=DB_DATABASE,
        )
        cursor = connection.cursor()
        # cursor.execute("TRUNCATE afd__incidents;")
        cursor.close()
    except (Exception, Error) as error:
        print("Error while connecting to PostgreSQL", error)

    print(data.shape)
    cursor = connection.cursor()
    for index, row in data.iterrows():
        if not index % 1000:
            print(str(index) + ":")

        if isinstance(row["X"], str):
            continue
        sql = "insert into afd__incidents (incident_number, ems_incident_number, call_datetime, calendar_year, jurisdiction, address, problem, flagged_incs, geometry) values (%s, %s, %s, %s, %s, %s, %s, %s, ST_SetSRID(ST_Point(%s, %s), 4326));"
        values = [
            row["Incident_Number"],
            row["EMS_IncidentNumber"],
            row["Inc_Date"].strftime("%Y-%m-%d")
            + " "
            + row["Inc_Time"].strftime("%H:%M:%S"),
            row["CalendarYear"],
            row["Jurisdiction"],
            row["CAD_Address"],
            row["CAD_Problem"],
            row["Flagged_Incs"],
            row["X"],
            row["Y"],
        ]

        cursor.execute(sql, values)
    connection.commit()

    if connection:
        connection.close()
        print("PostgreSQL connection is closed")


def get_timestamp():
    current = datetime.now()
    return f"{str(current.year)}-{str(current.month)}-{str(current.day)}-{str(current.hour)}-{str(current.minute)}-{str(current.second)}"


def main():
    # Get current timestamp
    timestamp = get_timestamp()

    # Initialize AWS clients and connect to S3 resources
    # aws_s3_resource = boto3.resource("s3")
    # my_bucket = aws_s3_resource.Bucket("atd-afd-incident-data")
    pp.pprint("Connecting to AWS S3 bucket...")
    aws_s3_client = boto3.client("s3")

    newest_object = get_most_recent_file("atd-afd-incident-data", aws_s3_client)
    contents = newest_object["Body"].read().decode("utf-8")

    # Given the s3 object content is the SES email,
    # get the message content and attachment using email package
    msg = email.message_from_string(contents)
    attachment = msg.get_payload()[1]
    # Write the attachment to a temp location
    open("/tmp/attach.xlsx", "wb").write(attachment.get_payload(decode=True))

    # Upload the file to an archive location in S3 bucket and append timestamp to the filename
    # Extracted attachment is temporarily saved as attach.xlsx and then uploaded as upload-<timestamp>.xlsx
    try:
        aws_s3_client.upload_file(
            "/tmp/attach.xlsx",
            "atd-afd-incident-data",
            "attachments/upload-" + timestamp + ".xlsx",
        )
        pp.pprint(f"Upload Successful")
    except FileNotFoundError:
        pp.pprint("The file was not found")

    # Extract the csv from email
    data = pandas.read_excel("/tmp/attach.xlsx", header=0)

    # TODO: Trim data to last 60 days

    upload_data_to_postgres(data)

    # Clean up the file from temp location
    os.remove("/tmp/attach.xlsx")


main()
