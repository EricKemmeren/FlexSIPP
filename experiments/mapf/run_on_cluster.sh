#!/bin/bash
#SBATCH --job-name=flex-sep
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=3GB
#SBATCH --time=01:00:00
#SBATCH --output=logs/%j.out
#SBATCH --error=logs/%j.err

# Load modules
module load 2026
module load gcc/13.3
module load boost/1.90
module load python/3.13

# Activate environment
cd /path/to/FlexSIPP
source .venv/bin/activate

# Run experiment
python experiments/mapf/sequential_delay_experiment.py
