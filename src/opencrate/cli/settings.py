from typing import List

from pydantic_settings import BaseSettings


class ConfigSetting(BaseSettings):
    title: str
    name: str
    version: str
    description: str
    datatypes: List[str]
    task: str
    framework: str
    logging: str
    logging_package: str
    python_version: str
    pull_docker_image: str
    docker_image: str
    entry_command: str
    docker_container: str
    runtime: str
    framework_runtime: str
    git_remote_url: str
