# EKAINE PKI Infra
- Uses [Smallstep](https://smallstep.com)
- Creates a dockerized CA server
- Generates certs for:
  - Postgres/Timescale DB
    - Prod runs on a self-hosted homelab
  - Grafana Cloud instance
  - Local dev
- Mainly just used for the PG <-> Grafana communication

# Whatdo
- `./bootstrap.sh` in this directory and generate base files
- `make up` and spin up CA server
- `./generate_certs.sh` in this directory to generate the PG, Grafana, and Dev certs.
  - To get a `.pem` key file: `openssl pkey -in in.key -out out.key.pem`