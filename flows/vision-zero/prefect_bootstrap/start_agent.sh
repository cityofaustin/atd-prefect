#!/bin/sh

prefect auth login -k $VZ_PREFECT_API_KEY
#prefect agent local start --no-hostname-label -l vision-zero -l atd-data03
tail -f /dev/null