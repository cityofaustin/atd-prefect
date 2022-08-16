#!/bin/bash

clear;
#rm output_log;
black ./test_instance_deployment/atd-moped/moped-etl/prefect/moped_test_create_flow.py 
black ./test_instance_deployment/atd-moped/moped-etl/prefect/tasks/ecs.py;
black ./test_instance_deployment/atd-moped/moped-etl/prefect/tasks/netlify.py;
black ./test_instance_deployment/atd-moped/moped-etl/prefect/tasks/api.py;
black ./test_instance_deployment/atd-moped/moped-etl/prefect/tasks/database.py;
#python3 ./test_instance_deployment/atd-moped/moped-etl/prefect/moped_test_create_flow.py | tee output_log; vim output_log;
python3 ./test_instance_deployment/atd-moped/moped-etl/prefect/moped_test_create_flow.py 
