import os
from typing import Dict, List

from pydantic_settings import BaseSettings

from .utils import write_template


class ConfigSetting(BaseSettings):
    title: str
    name: str
    version: str
    description: str
    datatypes: str
    python_version: str
    pull_docker_image: str
    docker_image: str
    entry_command: str
    docker_container: str
    runtime: str
    git_remote_url: str

    # docker_registry: str = "opencrate"
    # docker_base_image: str = "nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04"
    # docker_base_image_cpu: str = "ubuntu:22.04"

    def write_template_settings(
        self, config: Dict[str, str], template_item_paths: List[str]
    ):
        config_path = os.path.join(config["project_dir"], ".opencrate", "config.json")
        with open(config_path, "w") as json_file:
            json_file.write(self.model_dump_json(indent=4))

        for item_path in template_item_paths:
            write_template(os.path.join(config["project_dir"], item_path), self)
