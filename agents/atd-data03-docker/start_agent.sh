#!/bin/sh

prefect auth login -k $VZ_PREFECT_API_KEY
prefect agent docker start -l docker -l atd-data03 -l production
