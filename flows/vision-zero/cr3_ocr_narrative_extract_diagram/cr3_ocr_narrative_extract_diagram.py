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

RAW_AIRFLOW_CONFIG_JSON = os.getenv("RAW_AIRFLOW_CONFIG")
RAW_AIRFLOW_CONFIG = json.loads(RAW_AIRFLOW_CONFIG_JSON)

#AWS_DEFAULT_REGION = kv_dictionary["AWS_DEFAULT_REGION"]

HASURA_ENDPOINT = RAW_AIRFLOW_CONFIG["HASURA_ENDPOINT"]
HASURA_ADMIN_KEY = RAW_AIRFLOW_CONFIG["HASURA_ADMIN_KEY"]
AWS_DEFALUT_REGION = RAW_AIRFLOW_CONFIG["AWS_DEFALUT_REGION"]
AWS_ACCESS_KEY_ID = RAW_AIRFLOW_CONFIG["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY = RAW_AIRFLOW_CONFIG["AWS_SECRET_ACCESS_KEY"]

env = { 'HASURA_ENDPOINT': HASURA_ENDPOINT, 'HASURA_ADMIN_KEY': HASURA_ADMIN_KEY,
        'AWS_DEFALUT_REGION': AWS_DEFALUT_REGION, 'AWS_ACCESS_KEY_ID': AWS_ACCESS_KEY_ID, }

task = ShellTask(return_all=True, log_stderr=True, env=env)

with Flow(
    "CR3 Narrative OCR and Diagram Extraction",
    # schedule=Schedule(clocks=[CronClock("* * * * *")]),
    run_config=UniversalRun(labels=["vision-zero", "atd-data03"]),
) as flow:
    logger = prefect.context.get("logger")

    # see https://github.com/cityofaustin/atd-airflow/blob/master/dags/python_scripts/cr3_extract_diagram_ocr_narrative.py#L15-L25

    # real deal
    #command = "/usr/bin/python3 /root/cr3_ocr_narrative_extract_diagram/atd-airflow/dags/python_scripts/cr3_extract_diagram_ocr_narrative.py -v -d --update-narrative --update-timestamp --batch 100 --cr3-source atd-vision-zero-editor production/cris-cr3-files --save-diagram-s3 atd-vision-zero-website cr3_crash_diagrams/production "

    # testing real deal but a single crash id
    command = "/usr/bin/python3 /root/cr3_ocr_narrative_extract_diagram/atd-airflow/dags/python_scripts/cr3_extract_diagram_ocr_narrative.py -v -d --update-narrative --update-timestamp --crash-id 18884123 --cr3-source atd-vision-zero-editor production/cris-cr3-files --save-diagram-s3 atd-vision-zero-website cr3_crash_diagrams/production "

    # do no thing but on one crash id
    #command = "/usr/bin/python3 /root/cr3_ocr_narrative_extract_diagram/atd-airflow/dags/python_scripts/cr3_extract_diagram_ocr_narrative.py -vd --cr3-source atd-vision-zero-editor production/cris-cr3-files --save-diagram-disk /root/output/ --crash-id 18884123"

    stream = task.run(command=command)

    print("\n".join(stream))
    #logger.info(stream)


# I'm not sure how to make this not self-label by the hostname of the registering computer.
# here, it only tags it with the docker container ID, so no harm, no foul, but it's noisy.
#flow.register(project_name="vision-zero")
flow.run()
