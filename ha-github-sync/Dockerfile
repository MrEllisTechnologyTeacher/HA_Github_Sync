ARG BUILD_FROM
FROM $BUILD_FROM

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install runtime dependencies
RUN apk add --no-cache \
    git \
    openssh-client \
    py3-yaml \
    && rm -rf /var/cache/apk/*

# Copy the sync package into the container as a proper Python package
COPY sync/ /opt/ha-github-sync/ha_github_sync/

# Copy the entrypoint script
COPY run.sh /run.sh
RUN chmod a+x /run.sh

CMD ["/run.sh"]
