FROM debian:bullseye
RUN apt -y update &&\
    apt -y install curl jq &&\
    apt -y clean
COPY update.sh /update.sh

ENTRYPOINT ["/update.sh"]
