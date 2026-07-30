#!/bin/bash
#SBATCH --job-name=flex-ind
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem-per-cpu=3GB
#SBATCH --time=08:00:00
#SBATCH --output=logs/%A-%a.out
#SBATCH --error=logs/%A-%a.err

# Load modules
module load 2026
module load gcc/13.3
module load boost/1.90
module load python/3.13

# Load modules
module load 2026
module load gcc/13.3
module load boost/1.90
module load python/3.13

# Activate environment
cd /home/<netid>/FlexSIPP
rm -rf .venv
python -m venv .venv
source .venv/bin/activate
pip install --no-index --find-links=/home/<netid>/FlexSIPP/wheelhouse .


# Run experiment
/home/<netid>/FlexSIPP/experiments/mapf/individual_single_delay_experiment.py 1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50,51,52,53,54,55,56,57

