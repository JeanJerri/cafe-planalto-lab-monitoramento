#!/bin/sh
set -eu

export SMTP_SMARTHOST="${SMTP_SMARTHOST:-smtp.gmail.com:587}"
export SMTP_FROM="${SMTP_FROM:-alertas@cafeplanalto.lab}"
export SMTP_AUTH_USERNAME="${SMTP_AUTH_USERNAME:-alertas@cafeplanalto.lab}"
export SMTP_AUTH_PASSWORD="${SMTP_AUTH_PASSWORD:-not-configured}"
export SMTP_REQUIRE_TLS="${SMTP_REQUIRE_TLS:-true}"
export ALERT_EMAIL_TO="${ALERT_EMAIL_TO:-equipe@cafeplanalto.lab}"

if [ "${SMTP_AUTH_PASSWORD}" = "not-configured" ] || [ -z "${SMTP_AUTH_PASSWORD}" ]; then
    echo "[alertmanager] AVISO: SMTP_AUTH_PASSWORD nao configurada no .env; a interface web :9093 funcionara, mas o envio real de e-mail falhara ate configurar a senha SMTP."
fi

envsubst '${SMTP_SMARTHOST} ${SMTP_FROM} ${SMTP_AUTH_USERNAME} ${SMTP_AUTH_PASSWORD} ${SMTP_REQUIRE_TLS} ${ALERT_EMAIL_TO}' \
    < /etc/alertmanager/alertmanager.yml.tmpl \
    > /tmp/alertmanager.yml

/bin/amtool check-config /tmp/alertmanager.yml

exec /bin/alertmanager \
    --config.file=/tmp/alertmanager.yml \
    --storage.path=/alertmanager \
    "$@"
