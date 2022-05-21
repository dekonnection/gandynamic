FROM debian:bullseye
COPY update.sh /update.sh

ENTRYPOINT ["/update.sh"]
