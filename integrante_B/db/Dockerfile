FROM postgres:16-alpine

# iproute2 e necessario para o Containerlab executar ip addr e ip route no no db
RUN apk add --no-cache iproute2

COPY init.sql /docker-entrypoint-initdb.d/01-init.sql
