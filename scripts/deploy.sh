#!/usr/bin/env bash
set -euo pipefail

# Placeholder deploy script. Replace with real commands.
ssh ${DEPLOY_HOST:-ec2-user@your-host} 'cd /opt/meeting-police && docker compose pull && docker compose up -d'
