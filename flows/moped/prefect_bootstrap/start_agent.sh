#!/bin/sh

prefect auth login -k $PREFECT_API_KEY

dask-scheduler &
dask-worker tcp://172.25.0.2:8786 &
dask-worker tcp://172.25.0.2:8786 &
dask-worker tcp://172.25.0.2:8786 &

prefect agent local start -l moped --import-path /root/test_instance_deployment/atd-moped/moped-etl/prefect
