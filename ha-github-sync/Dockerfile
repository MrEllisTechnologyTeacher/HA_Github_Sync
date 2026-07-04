ARG BUILD_FROM
FROM $BUILD_FROM

SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Install runtime dependencies
RUN apk add --no-cache \
    git \
    openssh-client \
    && rm -rf /var/cache/apk/*

# Install Python dependencies (py3-yaml via apk targets the system Python,
# not the base image's Python, so we use pip instead)
RUN pip install --no-cache-dir PyYAML

# Copy the sync package into the container as a proper Python package
COPY sync/ /opt/ha-github-sync/ha_github_sync/

# Copy the entrypoint script
COPY run.sh /run.sh
RUN chmod a+x /run.sh

CMD ["/run.sh"]
