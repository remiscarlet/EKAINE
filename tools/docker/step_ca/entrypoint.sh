#!/bin/bash
set -e

STEP_HOME="/home/step"
CA_CONFIG="${STEP_HOME}/config/ca.json"

# Initialize CA only if not already initialized
if [ ! -f "${CA_CONFIG}" ]; then
  step ca init --name "$DOCKER_STEPCA_INIT_NAME" \
               --dns "$DOCKER_STEPCA_INIT_DNS_NAMES" \
               --provisioner admin \
               --password-file "$DOCKER_STEPCA_INIT_PASSWORD_FILE" \
               --provisioner-password-file "$DOCKER_STEPCA_INIT_PASSWORD_FILE" \
               --with-ca-url https://step-ca:9000
fi

exec step-ca "$CA_CONFIG" --password-file "$DOCKER_STEPCA_INIT_PASSWORD_FILE"