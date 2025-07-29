FROM {{pull_docker_image}}:latest


RUN python{{python_version}} -m pip install --upgrade pip --root-user-action=ignore
# COPY ./.opencrate/requirements.txt /home/workspace
# RUN pip install -r requirements.txt --root-user-action=ignore


CMD [ "{{entry_command}}" ]