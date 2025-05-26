docker exec -it ekaine_ca step ca certificate \
  db.ekaine.space certs/postgres.crt certs/postgres.key \
  --provisioner admin \
  --password-file /home/step/secrets/password.txt

docker exec -it ekaine_ca step ca certificate \
  grafana-client certs/grafana.crt certs/grafana.key \
  --provisioner admin \
  --password-file /home/step/secrets/password.txt

docker exec -it ekaine_ca step ca certificate \
  dev-client certs/localdev.crt certs/localdev.key \
  --provisioner admin \
  --password-file /home/step/secrets/password.txt