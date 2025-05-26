set -euo pipefail

mkdir -p config secrets certs

PASSWORD_FILE=secrets/password.txt

if [ ! -f "$PASSWORD_FILE" ]; then
  openssl rand -base64 32 | tr -d '\n' > "$PASSWORD_FILE"
  echo "Generated new CA password and saved to $PASSWORD_FILE"
fi

docker run --rm \
  -v "$(pwd)/config:/home/step/config" \
  -v "$(pwd)/secrets:/home/step/secrets" \
  -v "$(pwd)/certs:/home/step/certs" \
  -e DOCKER_STEPCA_INIT_NAME="ekaine-ca" \
  -e DOCKER_STEPCA_INIT_DNS_NAMES="localhost,ca.ekaine.space" \
  -e DOCKER_STEPCA_INIT_PASSWORD_FILE="/home/step/secrets/password.txt" \
  -e DOCKER_STEPCA_INIT_PROVISIONER_NAME="admin" \
  remiscarlet/ekaine_ca init
