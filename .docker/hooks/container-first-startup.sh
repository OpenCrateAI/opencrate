#!/bin/sh

# Check if the file exists and run once if file does not exist
if [ ! -f "/tmp/first_run_completed" ]; then
    echo "Running first-time setup..."

    git config --global user.name "$GIT_USER_NAME"
    git config --global user.email "$GIT_USER_EMAIL"
    
    touch /tmp/first_run_completed
    echo "First-time setup completed successfully."
fi
# Start your main application
exec "$@"