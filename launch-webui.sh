#!/bin/bash
# SBatch reservation and runtime configurations
#SBATCH --job-name DDx-Finder_webui
#SBATCH --output logs/%x/%j.log
#SBATCH --time 7-00:00:00
#SBATCH --partition Xeon

# CREATE AND RUN CONTAINER #####################################################
docker-compose up webui mcpo