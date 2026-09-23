FROM nginx:1.30.5-alpine

COPY nginx.conf /etc/nginx/nginx.conf
COPY conf.d/ /etc/nginx/conf.d/
RUN mkdir -p /etc/nginx/tls

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]
