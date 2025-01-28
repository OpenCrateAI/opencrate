# Default arguments for make commands
MAKEFLAGS += --no-print-directory

# Python interpreter
PYTHON ?= python3.9

# Script path
SCRIPT_PATH = .opencrate/makefile.py

# Define a function to run the script with given arguments
define run_script
	@$(PYTHON) $(SCRIPT_PATH) $(1) $(foreach var,$(2),$(var)="$($(var))")
endef

.PHONY: build start stop enter commit reset kill status

build: # running from host
	$(call run_script,build,)

start: # running from host
	$(call run_script,start,)

stop: # running from host
	$(call run_script,stop,)

enter: # running from host
	$(call run_script,enter,)

commit: # running from host & container
	$(call run_script,commit,message)

update: # running from host & container
	$(call run_script,update,message)

reset: # running from host
	$(call run_script,reset,)

kill: # running from host
	$(call run_script,kill,)

status: # running from host
	$(call run_script,status,)