#!/bin/bash


clear;
rm output_log;
black ./test_instance_deployment/atd-moped/moped-etl/prefect/moped_test_create_flow.py ./test_instance_deployment/atd-moped/moped-etl/prefect/tasks/ecs.py;
python3 ./test_instance_deployment/atd-moped/moped-etl/prefect/moped_test_create_flow.py | tee output_log; 
vim output_log;
