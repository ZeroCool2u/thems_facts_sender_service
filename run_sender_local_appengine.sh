#!/usr/bin/env bash
cd /home/theo/PycharmProjects/thems_facts/sender_service/ || exit
dev_appserver.py --application=facts-sender fact_sender_app.yaml
