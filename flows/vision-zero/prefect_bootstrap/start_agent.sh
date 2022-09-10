#!/bin/sh

prefect auth login -k $VZ_PREFECT_API_KEY
prefect agent local start -l vision-zero --import-path /root/cris_import --import-path /root/cris_import/atd-vz-data/atd-etl/app
