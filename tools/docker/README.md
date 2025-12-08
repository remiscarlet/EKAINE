## Docker
- Can provide a `.env` file in this directory if any environment variables for the docker-compose need to be overwritten
  - Eg, PG_PORT or SMALLSTEP_PORT
- Must provide one with an overridden `PG_DATA_PATH` on Macs. This is because of Docker VM (Mac) semantics and its access to /var/ paths.
