#!/usr/bin/env bash

set -o errexit;

function register_tasks() {
  # First make sure to log in...
  prefect auth login --key "${PREFECT_KEY}";

  # We need to retrieve the name of the project
  for FLOW_PROJECT in $(ls "../../projects/"); do
    # Then each individual file within the project
    for FLOW_FILE in $(find "../../projects/${FLOW_PROJECT}" -type f -name "*.py"); do
      echo "... ${FLOW_FILE}";
      prefect register --project "${FLOW_PROJECT}" --path "${FLOW_FILE}"
    done;
  done;
}
