FROM ghcr.io/netcracker/qubership-docker-integration-tests:main

RUN mkdir -p ${ROBOT_HOME}

COPY robot ${ROBOT_HOME}

# Fix permissions for non-root user (1000:0)
RUN chown -R 1000:0 ${ROBOT_HOME} && chmod -R 775 ${ROBOT_HOME}

# Switch back to non-root user for security compliance
USER 1000:0

EXPOSE 8080
