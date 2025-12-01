#!/bin/bash
# SBatch reservation and runtime configurations
#SBATCH --job-name DDx-Finder_vllm
#SBATCH --output logs/%x/%j.log
#SBATCH --time 7-00:00:00
#SBATCH --partition A100
#SBATCH --gres gpu:2

# CREATE AND RUN CONTAINER #####################################################
docker-compose up vllm