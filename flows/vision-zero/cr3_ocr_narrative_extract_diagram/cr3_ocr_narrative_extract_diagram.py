#!/usr/bin/python3

import os
import json
from subprocess import Popen, PIPE

# Import various prefect packages and helper methods
import prefect
from prefect import Flow
from prefect.backend import get_key_value
from prefect.schedules.clocks import CronClock
from prefect.run_configs import UniversalRun
from prefect.tasks.shell import ShellTask

kv_store = get_key_value("Vision Zero Development")
kv_dictionary = json.loads(kv_store)

HASURA_ENDPOINT = kv_dictionary["PRODUCTION_GRAPHQL_ENDPOINT"]
HASURA_ADMIN_KEY = kv_dictionary["PRODUCTION_GRAPHQL_ENDPOINT_ACCESS_KEY"]
AWS_DEFAULT_REGION = kv_dictionary["AWS_DEFAULT_REGION"]
AWS_ACCESS_KEY_ID = kv_dictionary["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = kv_dictionary["AWS_SECRET_ACCESS_KEY"]

env = { 'HASURA_ENDPOINT': HASURA_ENDPOINT, 'HASURA_ADMIN_KEY': HASURA_ADMIN_KEY,
        'AWS_DEFAULT_REGION': AWS_DEFAULT_REGION, 'AWS_ACCESS_KEY_ID': AWS_ACCESS_KEY_ID, }

task = ShellTask(return_all=True, log_stderr=True, env=env)

with Flow(
    "CR3 Narrative OCR and Diagram Extraction",
    # schedule=Schedule(clocks=[CronClock("* * * * *")]),
    run_config=UniversalRun(labels=["vision-zero", "atd-data03"]),
) as flow:
    logger = prefect.context.get("logger")

    # see https://github.com/cityofaustin/atd-airflow/blob/master/dags/python_scripts/cr3_extract_diagram_ocr_narrative.py#L15-L25

    # batch mode (production)
    #command = "/usr/bin/python3 \
      #/root/cr3_ocr_narrative_extract_diagram/atd-airflow/dags/python_scripts/cr3_extract_diagram_ocr_narrative.py \
      #--batch 100 \
      #-vd --update-narrative --update-timestamp \
      #--cr3-source atd-vision-zero-editor production/cris-cr3-files \
      #--save-diagram-s3 atd-vision-zero-website cr3_crash_diagrams/production "

    # a single crash ID (testing)
    command = "/usr/bin/python3 \
        /root/cr3_ocr_narrative_extract_diagram/atd-airflow/dags/python_scripts/cr3_extract_diagram_ocr_narrative.py \
        --crash-id 18884123 \
        -vd --update-narrative --update-timestamp \
        --cr3-source atd-vision-zero-editor production/cris-cr3-files \
        --save-diagram-s3 atd-vision-zero-website cr3_crash_diagrams/production"

    stream = task.run(command=command)

    logger.info("\n".join(stream))

flow.run()
