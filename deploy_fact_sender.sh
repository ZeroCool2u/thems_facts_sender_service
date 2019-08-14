#!/usr/bin/env bash
cd /home/theo/PycharmProjects/thems_facts/sender_service || exit
gcloud app deploy ./fact_sender_app.yaml --quiet
