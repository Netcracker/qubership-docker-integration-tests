# hadolint global ignore=DL3013,DL3018
FROM python:3.13-alpine3.22

ENV ROBOT_HOME=/opt/robot \
    PYTHONPATH=/usr/local/lib/python3.13/site-packages/integration_library_builtIn \
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

RUN \
    # Install dependencies
    apk add --update --no-cache \
        bash \
        shadow \
        vim \
        rsync \
        ttyd \
        build-base \
        apk-tools \
        py3-yaml \
        ca-certificates \
    # Clean up
    && rm -rf /var/cache/apk/*

RUN echo 'https://dl-cdn.alpinelinux.org/alpine/edge/testing' >> /etc/apk/repositories \
    && apk add --update --no-cache \
        s5cmd \
    # Clean up
    && rm -rf /var/cache/apk/*

RUN \
    # Add an unprivileged user
    groupadd -r robot --gid=${GROUP_ID} \
    && useradd -s /bin/bash -r -g robot --uid=${USER_ID} robot \
    && usermod -a -G 0 robot \
    # Install dependencies
    && python3 -m pip install --no-cache-dir --upgrade \
        pip \
        setuptools \
    && python3 -m pip install --no-cache-dir -r ${ROBOT_HOME}/requirements.txt \
    && python3 -m pip install --no-cache-dir ${ROBOT_HOME}/integration-tests-built-in-library \
    # Clean up
    && rm -rf ${ROBOT_HOME}/integration-tests-built-in-library \
    # Set permissions
    && chmod +x /docker-entrypoint.sh \
    && chmod -R 775 ${ROBOT_HOME}/scripts/adapter-S3 \
    && chgrp 0 /docker-entrypoint.sh

WORKDIR ${ROBOT_HOME}

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["run-robot"]

