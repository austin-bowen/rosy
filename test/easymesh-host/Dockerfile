# For testing nodes on a non-local host

FROM ubuntu:latest

# Avoid user interaction during package installation
ENV DEBIAN_FRONTEND=noninteractive

RUN apt update
RUN apt full-upgrade -y
RUN apt auto-remove -y
RUN apt install -y python3 python3-pip python3-venv
RUN apt clean

RUN python3 -m venv /venv

RUN echo "source /venv/bin/activate" >> /root/.bashrc

VOLUME ["/easymesh"]

WORKDIR /easymesh

ENTRYPOINT ["/easymesh/test/easymesh-host/entrypoint"]
