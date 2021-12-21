import json
import os
import datetime
import time

import requests
import random

# Other libraries
from string import Template
import knackpy


def gather_date_parameters(now=None):
    """
    Returns a tuple with the previous year and month from now.
    By default now is 'now', but it can be overridden by passing any datetime object.
    :param datetime now: The datetime to be considered as 'now'
    :return: int, int
    """
    now = datetime.datetime.now() if now is None else now
    last_month = now.month - 1 if now.month > 1 else 12
    last_year = now.year if now.month > 1 else now.year - 1
    return last_year, last_month


def month_number_to_name(month):
    """
    Returns a string with the name of the month based on a number from 1 to 12.
    :param int month: The month number: 1-January, 12-december
    :return str:
    """
    return datetime.date(1900, month, 1).strftime('%B')


def generate_graphql_query():
    """
    Generates a GraphQL query to be executed on Hasura
    :return str:
    """
    year, month = gather_date_parameters()

    return Template("""
        query atdGetMonthlyReport {
          api_atd_mds_monthy_trips(where: { year: {_eq: $year}, month: {_eq: $month} }) {
            field_62: provider { knack_id }
            field_70: year
            field_69: month
            field_63: total_trips
            field_64: total_trip_miles
            field_65: trip_length_avg
            field_66: trip_duration_avg
            field_67: trips_zero_distance
            field_68: trips_long_distance
            field_106: date_received
          }
        }
    """).substitute(
        year=year,
        month=month
    )


def gather_data_http_request():
    """
    Gathers the report data from Hasura
    :return dict:
    """
    query = generate_graphql_query()
    response = requests.post(
        url=os.getenv("mds_endpoint"),
        headers={
            "Accept": "*/*",
            "content-type": "application/json",
            "x-hasura-admin-secret": os.getenv("mds_endpoint_token")
        },
        json={
            "query": query
        }
    )
    response.encoding = "utf-8"
    return response.json()


def clean_up_record(record):
    """
    Modifies certain fields for a record dictionary.
    :param dict record:
    :return dict:
    """
    if record is None:
        return record

    # The provider ID is actually nested, we need to move it one level up.
    record["field_62"] = record["field_62"]["knack_id"]
    # We don't need the month number, but the month name:
    record["field_69"] = month_number_to_name(record["field_69"])
    # We need to add the user id for knack reporting (created_by field):
    record["field_73"] = os.getenv("knack_etl_user_id")
    # We also assign the create date field:
    record["field_74"] = datetime.date.today().strftime('%m/%d/%Y')
    return record


#
# First, let's gather the data
#
print("Gathering records from MDS...")
data = gather_data_http_request()

#
# We need to clean and add fields to each record
#
print("Cleaning Records...")
data = list(
    map(
        clean_up_record,
        data["data"]["api_atd_mds_monthy_trips"]
    )
)

#
# Insert to knack
#
"""
    Dealing with Knack failures.

    Whenever we deal with a Knack 503 failure, we have at least two good options:
    1. Roll back any previous changes and try again (hoping that next run will go smooth).
    2. Re-attempt every failed run until knack responds with an HTTP 200-OK.
    
    The first option requires a lot more code that needs testing, and I am not confident it's
    the best way moving forward. The second option I think gives us less code to write
    and we have the freedom to re-attempt to insert a single record as many times as needed.
    
    This report is important so I think it needs to keep trying to insert as many times as it
    has to until either Knack has time to respond to the request or the DAG gives up.
"""

print("Inserting records into knack...")
for record in data:
    print("Processing: ", record)
    done = False
    while not done:
        try:
            app = knackpy.App(app_id=os.getenv("knack_app_id"),  api_key=os.getenv("knack_api_key"))
            response = app.record(method="create", data=record, obj=os.getenv("knack_object"))
            print("Response: ", response, "\n")
            done = True
        except requests.exceptions.HTTPError as e:
            print("Error: ", str(e), "\n")
            lapse = random.randrange(10, 15)
            print("Trying again in " + str(lapse) + " seconds")
            time.sleep(lapse)
            done = False
