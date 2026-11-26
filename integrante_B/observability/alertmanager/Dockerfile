FROM prom/alertmanager:v0.27.0 AS ambin

FROM alpine:3.20

RUN apk add --no-cache \
    iproute2 \
    curl \
    ca-certificates \
    gettext

RUN mkdir -p /etc/alertmanager /alertmanager

COPY --from=ambin /bin/alertmanager /bin/alertmanager
COPY --from=ambin /bin/amtool /bin/amtool

COPY alertmanager.yml.tmpl /etc/alertmanager/alertmanager.yml.tmpl
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

EXPOSE 9093

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
