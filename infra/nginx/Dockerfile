FROM nginx:1.30.5-alpine

COPY nginx.conf /etc/nginx/nginx.conf
RUN rm -f /etc/nginx/conf.d/default.conf && mkdir -p /etc/nginx/tls /etc/nginx/templates
COPY templates/ /etc/nginx/templates/
ENV NGINX_ENVSUBST_FILTER="^SOPHIE_HOST$"

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]
