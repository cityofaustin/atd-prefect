#!/usr/bin/env python

"""
Name: EMS Incident Uploads
Description: This flow uploads EMS Incident Response CSVs (EMS Contact: Lynn C). 
    The data is emailed to atd-ems-incident-data@austinmobility.io daily ~ 3:30AM. From there it
    gets forwarded to a S3 bucket via AWS Simple Email Serivce.
Schedule: Daily at 03:30
Labels: test
"""

from prefect import Flow, task
from prefect.storage import GitHub
from prefect.run_configs import UniversalRun
from prefect.backend import get_key_value
from prefect.tasks.shell import ShellTask


FLOW_NAME = "ems_incident_upload"
environment_variables = get_key_value(key="vision_zero_staging")


# Configure code storage
STORAGE = GitHub(
    repo="cityofaustin/atd-prefect",
    path=f"flows/vision_zero/{FLOW_NAME}.py",
    ref="mc_8159_afd_etl_prefect",
)

ems_script = ShellTask(
    name="ems_script",
    command="python3 ./flows/vision_zero/python_scripts/ems_script.py",
    env=environment_variables,
    stream_output=True,
)

with Flow(
    FLOW_NAME,
    storage=STORAGE,
    run_config=UniversalRun(
        labels=["atd-data02", "staging"], env={"EXTRA_PIP_PACKAGES": "pandas"}
    ),
) as f:
    ems_script()


# f.run()
# f.visualize()
f.register(project_name="vision-zero")
