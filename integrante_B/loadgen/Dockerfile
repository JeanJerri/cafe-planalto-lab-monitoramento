FROM grafana/k6:0.54.0 AS k6bin

FROM alpine:3.20

RUN apk add --no-cache \
    iproute2 \
    iputils \
    traceroute \
    curl \
    bind-tools \
    ca-certificates

COPY --from=k6bin /usr/bin/k6 /usr/bin/k6

WORKDIR /loadgen

COPY script.js entrypoint.sh ./
RUN chmod +x /loadgen/entrypoint.sh

ENV TARGET_URL="http://loja.cafeplanalto.lab" \
    TARGET_RPS="10" \
    STARTUP_DELAY="5"

ENTRYPOINT ["/loadgen/entrypoint.sh"]
