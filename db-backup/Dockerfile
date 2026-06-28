FROM alpine:3.18

RUN apk update && \
    apk add --no-cache postgresql15-client rclone bash tar

WORKDIR /backup
COPY backup.sh /backup.sh
RUN chmod +x /backup.sh

ENTRYPOINT ["/backup.sh"]
