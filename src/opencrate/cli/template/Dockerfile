FROM {{pull_docker_image}}:latest


RUN apt update && apt upgrade -y && python{{python_version}} -m pip install --upgrade pip --root-user-action=ignore
# COPY ./.opencrate/requirements.txt /home/workspace
# RUN pip install -r requirements.txt --root-user-action=ignore
# RUN pip freeze > requirements.txt

CMD [ {{entry_command}} ]