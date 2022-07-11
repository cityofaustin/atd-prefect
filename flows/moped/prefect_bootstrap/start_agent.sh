#!/bin/sh

prefect auth login -k $VZ_PREFECT_API_KEY
prefect agent local start -l moped -l atd-data03
