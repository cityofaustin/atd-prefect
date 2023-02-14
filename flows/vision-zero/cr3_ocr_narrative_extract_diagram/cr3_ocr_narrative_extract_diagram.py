#!/usr/bin/python3

import json

import prefect
from prefect import Flow
from prefect.backend import get_key_value
from prefect.schedules.clocks import CronClock
from prefect.run_configs import UniversalRun
from prefect.tasks.shell import ShellTask

kv_store = get_key_value("Vision Zero")
kv_dictionary = json.loads(kv_store)

HASURA_ENDPOINT = kv_dictionary["PRODUCTION_GRAPHQL_ENDPOINT"]
HASURA_ADMIN_KEY = kv_dictionary["PRODUCTION_GRAPHQL_ENDPOINT_ACCESS_KEY"]
AWS_DEFAULT_REGION = kv_dictionary["AWS_DEFAULT_REGION"]
AWS_ACCESS_KEY_ID = kv_dictionary["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = kv_dictionary["AWS_SECRET_ACCESS_KEY"]

OCR_CR3_SOURCE_BUCKET = kv_dictionary["OCR_CR3_SOURCE_BUCKET"]
OCR_CR3_SOURCE_PATH = kv_dictionary["OCR_CR3_SOURCE_PATH"]
OCR_DIAGRAM_TARGET_BUCKET = kv_dictionary["OCR_DIAGRAM_TARGET_BUCKET"]
OCR_DIAGRAM_TARGET_PATH = kv_dictionary["OCR_DIAGRAM_TARGET_PATH"]
OCR_BATCH_SIZE = kv_dictionary["OCR_BATCH_SIZE"]
OCR_SINGLE_CRASH = kv_dictionary["OCR_SINGLE_CRASH"]

env = {
    "HASURA_ENDPOINT": HASURA_ENDPOINT,
    "HASURA_ADMIN_KEY": HASURA_ADMIN_KEY,
    "AWS_DEFAULT_REGION": AWS_DEFAULT_REGION,
    "AWS_ACCESS_KEY_ID": AWS_ACCESS_KEY_ID,
    "AWS_SECRET_ACCESS_KEY": AWS_SECRET_ACCESS_KEY,
}

task = ShellTask(return_all=True, log_stderr=True, stream_output=True, env=env)

with Flow(
    "CR3 Narrative OCR and Diagram Extraction",
    # schedule=Schedule(clocks=[CronClock("* * * * *")]),
    run_config=UniversalRun(labels=["vision-zero", "atd-data03"]),
) as flow:
    logger = prefect.context.get("logger")

    # see https://github.com/cityofaustin/atd-airflow/blob/master/dags/python_scripts/cr3_extract_diagram_ocr_narrative.py#L15-L25

    op_mode = (
        f"--crash-id {OCR_SINGLE_CRASH} "
        if OCR_SINGLE_CRASH
        else f"--batch {OCR_BATCH_SIZE} "
    )
    command = (
        f"/usr/bin/python3 \
        /root/cr3_ocr_narrative_extract_diagram/atd-airflow/dags/python_scripts/cr3_extract_diagram_ocr_narrative.py "
        + op_mode
        + f"-vd --update-narrative --update-timestamp \
        --cr3-source {OCR_CR3_SOURCE_BUCKET} {OCR_CR3_SOURCE_PATH} \
        --save-diagram-s3 {OCR_DIAGRAM_TARGET_BUCKET} {OCR_DIAGRAM_TARGET_PATH}"
    )

    stream = task(command=command)

    logger.info(stream)

#flow.run()
flow.register(project_name="vision-zero")
