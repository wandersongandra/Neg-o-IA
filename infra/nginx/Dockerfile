FROM nginx:1.31.7-alpine@sha256:892bb2152464f0c5d8972593a5f5afaf8054552580b699d95f8ff4af08c2d33d

COPY nginx.conf /etc/nginx/nginx.conf
RUN rm -f /etc/nginx/conf.d/default.conf && mkdir -p /etc/nginx/tls /etc/nginx/templates
COPY templates/ /etc/nginx/templates/
ENV NGINX_ENVSUBST_FILTER="^SOPHIE_HOST$"

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]
