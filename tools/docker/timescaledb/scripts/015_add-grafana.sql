create user grafana with password 'grafana_pw';
create database grafana_meta owner grafana;

grant connect on database grafana_meta to grafana;
grant connect on database grafana_meta to ekaine;
