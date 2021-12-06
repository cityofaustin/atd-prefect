#!/usr/bin/env bash

set -o errexit;

export BUCKET_NAME="atd-prefect";

#
# Determine working stage based on branch name
#
case "${BRANCH_NAME}" in
  "production")
    export WORKING_STAGE="production";
  ;;
  *)
    export WORKING_STAGE="staging";
  ;;
esac

# Centralizes the exit with a message
function exit_with_error() {
  echo "$1";
  exit 1;
}

# Removes any checksum files
function clean_up_checksums() {
  rm -rf *.md5sum;
}

# Generates an md5 for a file name
function get_md5_for_filename() {
  echo -n $1 | md5sum | cut -d " " -f 1;
}

# Generates md5 for the contents of a file
function get_md5_from_file() {
  md5sum $1 | cut -d " " -f 1;
}


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
