#!/usr/bin/env bash

set -o errexit;

function register_tasks() {
  # First make sure to log in...
  prefect auth login --key "${PREFECT_KEY}";

  # For each of the flow files
  for FLOW_FILE in $(grep -rl "__main__" flows); do
    # Extract the project name
    FLOW_PROJECT=$(echo "${FLOW_FILE}" | cut -d "/" -f 2);
    echo "Processing flow file: ${FLOW_FILE} (project name: ${FLOW_PROJECT})";
    # Register the flow file using the folder name as the project name
    prefect register --project $FLOW_PROJECT --path $FLOW_FILE;
  done;
}
