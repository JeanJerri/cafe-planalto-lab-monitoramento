FROM nginx:1.27-alpine

# iproute2 e curl sao necessarios para o Containerlab configurar rede e rotas no no web
RUN apk add --no-cache iproute2 curl

# Restringe envsubst estritamente a API_UPSTREAM para preservar variaveis do Nginx ($uri, $status, etc.)
ENV API_UPSTREAM="api:8000" \
    NGINX_ENVSUBST_FILTER="^API_UPSTREAM$"

COPY nginx.conf /etc/nginx/nginx.conf
COPY templates/default.conf.template /etc/nginx/templates/default.conf.template
COPY html/index.html /usr/share/nginx/html/index.html

EXPOSE 80 8080
