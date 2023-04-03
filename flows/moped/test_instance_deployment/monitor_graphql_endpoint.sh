#!/bin/bash

while sleep 2; do (cd /tmp/atd-moped/moped-database; hasura --skip-update-check metadata inconsistency status;); done