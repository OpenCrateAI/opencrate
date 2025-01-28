FROM {{pull_docker_image}}:latest


COPY ./.opencrate/requirements.txt /home/workspace
RUN pip install -r requirements.txt --no-cache-dir --use-deprecated=legacy-resolver
RUN pip freeze > requirements.txt

CMD [ {{entry_command}} ]