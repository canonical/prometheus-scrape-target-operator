#!/usr/bin/env python3
# Copyright 2022 Canonical Ltd.
# See LICENSE file for licensing details.


import logging
from pathlib import Path

import pytest
import yaml

logger = logging.getLogger(__name__)

METADATA = yaml.safe_load(Path("./metadata.yaml").read_text())
app_name = METADATA["name"]
config = {"targets": "1.2.3.4:5678", "metrics_path": "/foometrics"}


@pytest.mark.abort_on_fail
async def test_deploy_from_local_path(ops_test, charm_under_test):
    """Deploy the charm-under-test."""
    logger.debug("deploy local charm")

    resources = {"unused-image": METADATA["resources"]["unused-image"]["upstream-source"]}
    await ops_test.model.deploy(charm_under_test, application_name=app_name, resources=resources)

    await ops_test.model.applications[app_name].set_config(config)
    await ops_test.model.wait_for_idle(apps=[app_name], timeout=1000)

    # without any relations, the charm should be blocked
    assert ops_test.model.applications[app_name].units[0].workload_status == "blocked"


@pytest.mark.abort_on_fail
async def test_kubectl_delete_pod(ops_test):
    pod_name = f"{app_name}-0"

    cmd = [
        "sg",
        "microk8s",
        "-c",
        " ".join(["microk8s.kubectl", "delete", "pod", "-n", ops_test.model_name, pod_name]),
    ]

    logger.debug(
        "Removing pod '%s' from model '%s' with cmd: %s", pod_name, ops_test.model_name, cmd
    )

    retcode, stdout, stderr = await ops_test.run(*cmd)
    assert retcode == 0, f"kubectl failed: {(stderr or stdout).strip()}"
    logger.debug(stdout)
    await ops_test.model.block_until(lambda: len(ops_test.model.applications[app_name].units) > 0)
    await ops_test.model.wait_for_idle(apps=[app_name], timeout=1000)

    # without any relations, the charm should be blocked
    assert ops_test.model.applications[app_name].units[0].workload_status == "blocked"

    assert await ops_test.model.applications[app_name].get_config() == config
