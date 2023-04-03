#!/bin/sh

docker login --username $DOCKER_HUB_USERNAME --password $DOCKER_HUB_ACCESS_TOKEN

prefect auth login -k $VZ_PREFECT_API_KEY
prefect agent docker start -l docker -l atd-data03 -l production

