#!/bin/bash

# Check if git_remote_url is provided as an argument
git_remote_url=$1

# Initialize a new git repository
git init &> /dev/null

# Add all files to the staging area
git add . &> /dev/null

# Commit the changes
git commit -m 'opencrate initial commit' &> /dev/null

# # Add the remote repository
# git remote add origin "$git_remote_url"

# # Push the changes to the remote repository
# git push -u origin dev-v0