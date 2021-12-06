#!/usr/bin/env bash

set -o errexit;

# Registers the tasks
function register_tasks() {
  # First make sure to log in...
  prefect auth login --key "${PREFECT_KEY}";

  # For each of the flow files
  for FLOW_FILE in $(grep -rl "__main__" flows); do
    if [[ $(flow_needs_redeploy "${FLOW_FILE}") == "True" ]]; then
      # Extract the project name
      FLOW_PROJECT=$(echo "${FLOW_FILE}" | cut -d "/" -f 2);
      echo "Processing flow file: ${FLOW_FILE} (project name: ${FLOW_PROJECT})";
      # Register the flow file using the folder name as the project name
      prefect register --project $FLOW_PROJECT --path $FLOW_FILE;
    else
      # Nothing to do, ignore...
      echo "❯❯❯ Success: '${FLOW_FILE}' (flow does not need redeploy, skipping)";
    fi;
  done;

  # Wipe out any checksum files
  clean_up_checksums;
}
