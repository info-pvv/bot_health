FROM postgres:15-alpine

ENV POSTGRES_USER=admin
ENV POSTGRES_PASSWORD=password
ENV POSTGRES_DB=health_tracker

COPY init.sql /docker-entrypoint-initdb.d/