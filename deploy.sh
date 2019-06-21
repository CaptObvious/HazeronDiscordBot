#!/bin/sh

apk add --update python python-dev py-pip
pip install awscli --upgrade

export AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID
export AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY

aws ecs update-service --cluster hazeron-discord-bot --service hazeron-discord-bot-service --region us-west-2 --force-new-deployment
