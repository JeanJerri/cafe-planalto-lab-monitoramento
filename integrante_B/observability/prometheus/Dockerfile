FROM prom/prometheus:v2.55.1 AS prombin

FROM alpine:3.20

RUN apk add --no-cache \
    iproute2 \
    curl \
    ca-certificates

RUN mkdir -p /etc/prometheus/rules /prometheus

COPY --from=prombin /bin/prometheus /bin/prometheus
COPY --from=prombin /bin/promtool /bin/promtool
COPY --from=prombin /usr/share/prometheus/console_libraries /usr/share/prometheus/console_libraries
COPY --from=prombin /usr/share/prometheus/consoles /usr/share/prometheus/consoles

COPY prometheus.local.yml /etc/prometheus/prometheus.yml
COPY rules/alerts.yml /etc/prometheus/rules/alerts.yml

EXPOSE 9090

ENTRYPOINT ["/bin/prometheus"]
CMD [
  "--config.file=/etc/prometheus/prometheus.yml",
  "--storage.tsdb.path=/prometheus",
  "--storage.tsdb.retention.time=7d",
  "--web.console.libraries=/usr/share/prometheus/console_libraries",
  "--web.console.templates=/usr/share/prometheus/consoles",
  "--web.enable-lifecycle"
]
