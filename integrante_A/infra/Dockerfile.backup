FROM alpine:3

RUN apk add --no-cache \
    iproute2 \
    iputils \
    traceroute \
    procps

CMD ["sh", "-c", "while true; do sleep 3600; done"]
