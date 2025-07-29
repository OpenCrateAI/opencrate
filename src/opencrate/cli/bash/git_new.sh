#!/bin/bash

version=$1
message=$2
current_branch=$3

# we need to check if this is run from dev branch and not main

git add . > /dev/null
git commit -m "opencrate dev release for v$version - $message" > /dev/null
git checkout main-v$((version-1))
git merge $current_branch > /dev/null
git add . > /dev/null
git commit -m "opencrate main release for v$version - $message" > /dev/null
git checkout -b main-v$version > /dev/null
git checkout -b dev-v$version > /dev/null