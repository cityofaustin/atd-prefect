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
esac;

# This environment variable is needed for flows
export PREFECT_CURRENT_ENVIRONMENT=$WORKING_STAGE;

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

# Downloads the md5 checksum from S3
function get_md5_from_cloud() {
  FILE_NAME_HASH=$(get_md5_for_filename $1);
  {
    aws s3 cp "s3://${BUCKET_NAME}/deploys/${WORKING_STAGE}/${FILE_NAME_HASH}.md5sum" "${FILE_NAME_HASH}.md5sum" --quiet;
    cat "${FILE_NAME_HASH}.md5sum";
  } || {
    exit_with_error "Error: Failed to download md5 sum for '${1}'";
  }
}

# Store md5 checksum on S3
function save_md5_on_cloud() {
  FILE_NAME=$1
  {
    MD5_FILE_NAME=$(get_md5_for_filename $FILE_NAME);
    MD5_FILE_CHECKSUM=$(get_md5_from_file $FILE_NAME);
    echo -n $MD5_FILE_CHECKSUM > "${MD5_FILE_NAME}.md5sum";
    aws s3 cp "${MD5_FILE_NAME}.md5sum" "s3://${BUCKET_NAME}/deploys/${WORKING_STAGE}/${MD5_FILE_NAME}.md5sum" --quiet;
    echo "❯❯❯ Updated: '${MD5_FILE_NAME}' (for file ${FILE_NAME})";
  } || {
    exit_with_error "Error: could not store md5 for '${FILE_NAME}'";
  }
}

# Returns true if flow needs redeploy
function flow_needs_redeploy() {
  [[ $(get_md5_from_file $1) != $(get_md5_from_cloud $1) ]] && echo "True" || echo "False";
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
      echo "❯❯❯ Deploying: '${FLOW_FILE}' (project name: ${FLOW_PROJECT})";

      # Register the flow file using the folder name as the project name
      prefect register --force --no-schedule \
        --project $FLOW_PROJECT \
        --path $FLOW_FILE;

      # If all is successful, then update the md5 file
      save_md5_on_cloud $FLOW_FILE;
    else
      # Nothing to do, ignore...
      echo "❯❯❯ Skipping: '${FLOW_FILE}' (flow does not need redeploy)";
    fi;
  done;

  # Wipe out any checksum files
  clean_up_checksums;
}
