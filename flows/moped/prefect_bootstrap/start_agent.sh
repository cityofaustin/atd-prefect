#!/bin/sh

prefect auth login -k $PREFECT_API_KEY
prefect agent local start -l moped --import-path /root/test_instance_deployment/atd-moped/moped-etl/prefect
