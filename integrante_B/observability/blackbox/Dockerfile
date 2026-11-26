FROM prom/blackbox-exporter:v0.25.0 AS blackboxbin

FROM alpine:3.20

# iproute2, iputils, curl e bind-tools permitem Containerlab e diagnostico ICMP/HTTP/DNS na filial
RUN apk add --no-cache \
    iproute2 \
    iputils \
    curl \
    bind-tools \
    ca-certificates

COPY --from=blackboxbin /bin/blackbox_exporter /bin/blackbox_exporter
COPY blackbox.yml /etc/blackbox_exporter/config.yml

EXPOSE 9115

ENTRYPOINT ["/bin/blackbox_exporter"]
CMD ["--config.file=/etc/blackbox_exporter/config.yml"]
