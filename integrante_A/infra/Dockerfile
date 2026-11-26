FROM alpine:3

RUN apk add --no-cache \
    iproute2 \
    iputils \
    traceroute \
    procps \
    net-snmp \
    net-snmp-tools

CMD ["sh", "-c", "while true; do sleep 3600; done"]
