FROM ubuntu:bionic
# Create user with minimal privileges
RUN groupadd -r testrunner && useradd -r -s /bin/false -g testrunner testrunner
# Create directory for testing
RUN mkdir /testspace
WORKDIR /testspace
# Set ownership
RUN chown -R testrunner:testrunner /testspace
# Set user
USER testrunner