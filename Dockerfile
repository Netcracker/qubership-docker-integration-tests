FROM python:3.13.3-alpine3.21

ENV ROBOT_HOME=/opt/robot \
    PYTHONPATH=/usr/local/lib/python3.13/site-packages/integration_library_builtIn \
    IS_ANALYZER_RESULT_ENABLED=true \
    IS_TAGS_RESOLVER_ENABLED=true \
    STATUS_WRITING_ENABLED=false \
    USER_ID=1000 \
    GROUP_ID=1000

COPY scripts/docker-entrypoint.sh /
COPY scripts/*.py ${ROBOT_HOME}/
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
        py3-yaml
    # Clean up
    && rm -rf /var/cache/apk/*

RUN \
    # Add unprivileged user
    groupadd -r robot --gid=${GROUP_ID} \
    && useradd -s /bin/bash -r -g robot --uid=${USER_ID} robot \
    && usermod -a -G 0 robot \
    # Install dependencies
    && python3 -m pip install --upgrade \
        pip \
        setuptools \
    && python3 -m pip install -r ${ROBOT_HOME}/requirements.txt \
    && python3 -m pip install --no-cache-dir ${ROBOT_HOME}/integration-tests-built-in-library \
    # Clean up
    && rm -rf ${ROBOT_HOME}/integration-tests-built-in-library \
    # Set permissions
    && set -x \
    && for path in \
         /docker-entrypoint.sh \
    ; do \
        chmod +x "$path"; \
        chgrp 0 "$path"; \
    done

WORKDIR ${ROBOT_HOME}

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["run-robot"]
