#!/usr/bin/env bash
cd /home/theo/PycharmProjects/thems_facts/sender_service
gcloud app deploy ./fact_sender_app.yaml --quiet
