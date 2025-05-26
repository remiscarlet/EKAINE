#!/bin/bash
set -e

CA_CONFIG="/home/step/config/ca.json"
PASSWORD_FILE="/home/step/secrets/password.txt"

if [ ! -f "$CA_CONFIG" ] || [ ! -f "$PASSWORD_FILE" ]; then
  echo "Missing CA config or password file. Did you run bootstrap.sh?"
  exit 1
fi

echo "Starting Smallstep CA..."
exec step-ca "$CA_CONFIG" --password-file "$PASSWORD_FILE"