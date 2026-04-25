FROM nginx:1.27-alpine
RUN rm /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/nginx.conf
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD wget -qO- http://localhost/health || exit 1
EXPOSE 80
