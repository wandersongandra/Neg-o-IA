FROM nginx:1.31.0-alpine@sha256:2f07d83bf561b506400dc183b1b2003803e39efbd22451f848adaba14d28c7c7

COPY nginx.conf /etc/nginx/nginx.conf
RUN rm -f /etc/nginx/conf.d/default.conf && mkdir -p /etc/nginx/tls /etc/nginx/templates
COPY templates/ /etc/nginx/templates/
ENV NGINX_ENVSUBST_FILTER="^SOPHIE_HOST$"

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]
