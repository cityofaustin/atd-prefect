#!/bin/sh

/etc/init.d/ssh start
prefect auth login -k $VZ_PREFECT_API_KEY
prefect agent local start --no-hostname-label -l vision-zero -l atd-data03 -l production --import-path /root/cris_import --import-path /root/cris_import/atd-vz-data/atd-etl/app
