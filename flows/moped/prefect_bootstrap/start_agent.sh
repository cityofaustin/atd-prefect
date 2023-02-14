#!/bin/sh

prefect auth login -k $PREFECT_API_KEY

dask-scheduler --dashboard-address :8787 &
dask-worker tcp://prefect-agent:8786 &
dask-worker tcp://prefect-agent:8786 &

prefect agent local start -l moped --import-path /root/test_instance_deployment/atd-moped/moped-etl/prefect
