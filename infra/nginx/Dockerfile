FROM nginx:1.31.8-alpine@sha256:785835ea65db4bba6f021acc0f3be91b0fef76a53fe41f8588c6698d2aed0606

COPY nginx.conf /etc/nginx/nginx.conf
RUN rm -f /etc/nginx/conf.d/default.conf && mkdir -p /etc/nginx/tls /etc/nginx/templates
COPY templates/ /etc/nginx/templates/
ENV NGINX_ENVSUBST_FILTER="^SOPHIE_HOST$"

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]
