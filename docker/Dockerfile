FROM python:3.13.5-alpine3.21

ENV ROBOT_HOME=/opt/robot
ENV PYTHONPATH=/usr/local/lib/python3.13/site-packages/integration_library_builtIn
ENV IS_ANALYZER_RESULT_ENABLED=true
ENV IS_TAGS_RESOLVER_ENABLED=true
ENV STATUS_WRITING_ENABLED=false

COPY docker/docker-entrypoint.sh /
COPY docker/requirements.txt ${ROBOT_HOME}/requirements.txt
COPY docker/robot_tags_resolver.py ${ROBOT_HOME}/robot_tags_resolver.py
COPY docker/analyze_result.py ${ROBOT_HOME}/analyze_result.py
COPY docker/write_status.py ${ROBOT_HOME}/write_status.py
COPY integration-tests-built-in-library ${ROBOT_HOME}/integration-tests-built-in-library

RUN set -x \
    && apk add --update --no-cache bash shadow python3 vim rsync ttyd build-base apk-tools py3-yaml

# Upgrade all tools to avoid vulnerabilities
RUN set -x && apk upgrade --no-cache --available

#Add unprivileged user
RUN set -x \
    && groupadd -r robot --gid=1000 \
    && useradd -s /bin/bash -r -g robot --uid=1000 robot \
    && usermod -a -G 0 robot

RUN set -x \
    && python3 -m ensurepip \
    && rm -r /usr/lib/python*/ensurepip \
    && pip3 install --upgrade pip setuptools \
    && pip3 install -r ${ROBOT_HOME}/requirements.txt \
    && pip3 install --no-cache-dir ${ROBOT_HOME}/integration-tests-built-in-library \
    && rm -rf ${ROBOT_HOME}/integration-tests-built-in-library \
    && rm -rf /var/cache/apk/*

RUN set -x \
    && for path in \
         /docker-entrypoint.sh \
    ; do \
        chmod +x "$path"; \
        chgrp 0 "$path"; \
    done

WORKDIR ${ROBOT_HOME}

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["run-robot"]
