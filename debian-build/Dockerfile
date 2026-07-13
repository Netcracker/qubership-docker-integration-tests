# hadolint global ignore=DL3013,DL3018
FROM python:3.14-slim

ENV ROBOT_HOME=/opt/robot \
    PYTHONPATH=/usr/local/lib/python3.14/site-packages/integration_library_builtIn \
    IS_ANALYZER_RESULT_ENABLED=true \
    IS_TAGS_RESOLVER_ENABLED=true \
    STATUS_WRITING_ENABLED=false \
    USER_ID=1000 \
    GROUP_ID=1000

COPY scripts/docker-entrypoint.sh /
COPY scripts/*.py ${ROBOT_HOME}/
COPY scripts/adapter-S3 ${ROBOT_HOME}/scripts/adapter-S3
COPY requirements.txt ${ROBOT_HOME}/requirements.txt
COPY library ${ROBOT_HOME}/integration-tests-built-in-library

ARG PIP="26.1.2"

RUN \
    # Install dependencies
    apt-get update \
    && apt-get install -y --no-install-recommends \
        tini \
        bash \
        passwd \
        vim \
        rsync \
        curl \
        build-essential \
        python3-yaml \
        ca-certificates \
        inotify-tools \
    && curl -L https://github.com/tsl0922/ttyd/releases/download/1.7.7/ttyd.x86_64 \
        -o /usr/local/bin/ttyd \
    && chmod +x /usr/local/bin/ttyd \
    # Clean up
    && rm -rf /var/lib/apt/lists/*

RUN ARCH=$(dpkg --print-architecture) \
    && if [ "$ARCH" = "amd64" ]; then FILE="s5cmd_2.3.0_Linux-64bit.tar.gz"; \
       elif [ "$ARCH" = "arm64" ]; then FILE="s5cmd_2.3.0_Linux-arm64.tar.gz"; \
       else echo "Unsupported architecture: $ARCH" && exit 1; fi \
    && curl -fL -o /tmp/s5cmd.tar.gz https://github.com/peak/s5cmd/releases/download/v2.3.0/${FILE} \
    && tar -xzf /tmp/s5cmd.tar.gz -C /tmp \
    && mv /tmp/s5cmd /usr/local/bin/s5cmd \
    && chmod +x /usr/local/bin/s5cmd \
    && rm -f /tmp/s5cmd.tar.gz

RUN \
    # Add an unprivileged user
    groupadd -r robot --gid=${GROUP_ID} \
    && useradd -s /bin/bash -r -g robot --uid=${USER_ID} robot \
    && usermod -a -G 0 robot \
    # Install dependencies
    && python3 -m pip install --no-cache-dir --upgrade \
        pip==${PIP} \
        setuptools \
    && python3 -m pip install --no-cache-dir -r ${ROBOT_HOME}/requirements.txt \
    && python3 -m pip install --no-cache-dir ${ROBOT_HOME}/integration-tests-built-in-library \
    # Clean up
    && rm -rf ${ROBOT_HOME}/integration-tests-built-in-library \
    # Create output directory
    && mkdir -p ${ROBOT_HOME}/output \
    # Set permissions
    && chmod +x /docker-entrypoint.sh \
    && chmod -R 775 ${ROBOT_HOME} \
    && chown -R ${USER_ID}:0 ${ROBOT_HOME} \
    && chgrp -R 0 ${ROBOT_HOME} \
    && chgrp 0 /docker-entrypoint.sh

WORKDIR ${ROBOT_HOME}

ENTRYPOINT ["/usr/bin/tini", "--", "/docker-entrypoint.sh"]
CMD ["run-robot"]
