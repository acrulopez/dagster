# pylint: disable=redefined-outer-name
import json
import os
import subprocess
from contextlib import contextmanager

import pytest

from .utils import BUILDKITE


@pytest.fixture(scope="module")
def docker_compose_cm(test_directory):
    @contextmanager
    def docker_compose(
        docker_compose_yml=None,
        network_name=None,
        docker_context=None,
    ):
        if not docker_compose_yml:
            docker_compose_yml = default_docker_compose_yml(test_directory)
        if not network_name:
            network_name = network_name_from_yml(docker_compose_yml)
        try:
            docker_compose_up(docker_compose_yml, docker_context)
            if BUILDKITE:
                # When running in a container on Buildkite, we need to first connect our container
                # and our network and then yield a dict of container name to the container's
                # hostname.
                with buildkite_hostnames_cm(network_name) as hostnames:
                    yield hostnames
            else:
                # When running locally, we don't need to jump through any special networking hoops;
                # just yield a dict of container name to "localhost".
                yield dict((container, "localhost") for container in list_containers())
        finally:
            docker_compose_down(docker_compose_yml, docker_context)

    return docker_compose


@pytest.fixture
def docker_compose(docker_compose_cm):
    with docker_compose_cm() as docker_compose:
        yield docker_compose


def docker_compose_up(docker_compose_yml, context):
    if context:
        compose_command = ["docker", "--context", context, "compose"]
    else:
        compose_command = ["docker-compose"]
    subprocess.check_call(
        compose_command
        + [
            "--file",
            str(docker_compose_yml),
            "up",
            "--detach",
        ]
    )


def docker_compose_down(docker_compose_yml, context):
    if context:
        compose_command = ["docker", "--context", context, "compose"]
    else:
        compose_command = ["docker-compose"]
    subprocess.check_call(
        compose_command
        + [
            "--file",
            str(docker_compose_yml),
            "down",
        ]
    )


def list_containers():
    # TODO: Handle default container names: {project_name}_service_{task_number}
    return subprocess.check_output(["docker", "ps", "--format", "{{.Names}}"]).decode().splitlines()


def current_container():
    container_id = subprocess.check_output(["cat", "/etc/hostname"]).strip().decode()
    container = (
        subprocess.check_output(
            ["docker", "ps", "--filter", f"id={container_id}", "--format", "{{.Names}}"]
        )
        .strip()
        .decode()
    )
    return container


def connect_container_to_network(container, network):
    subprocess.check_call(["docker", "network", "connect", network, container])


def disconnect_container_from_network(container, network):
    subprocess.check_call(["docker", "network", "disconnect", network, container])


def hostnames(network):
    hostnames = {}
    for container in list_containers():
        output = subprocess.check_output(["docker", "inspect", container])
        networking = json.loads(output)[0]["NetworkSettings"]
        hostname = networking["Networks"].get(network, {}).get("IPAddress")
        if hostname:
            hostnames[container] = hostname
    return hostnames


@contextmanager
def buildkite_hostnames_cm(network):
    container = current_container()

    try:
        connect_container_to_network(container, network)
        yield hostnames(network)

    finally:
        disconnect_container_from_network(container, network)


def default_docker_compose_yml(default_directory):
    if os.path.isfile("docker-compose.yml"):
        return os.path.join(os.getcwd(), "docker-compose.yml")
    else:
        return os.path.join(default_directory, "docker-compose.yml")


def network_name_from_yml(docker_compose_yml):
    dirname = os.path.dirname(docker_compose_yml)
    basename = os.path.basename(dirname)
    return basename + "_default"
