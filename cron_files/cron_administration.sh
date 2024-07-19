#!/bin/bash

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
export PYTHONPATH="$PYTHONPATH:$SCRIPT_DIR/../"
cd "$SCRIPT_DIR/../src/data_acquisition" || exit
python data_acquisition_manager.py -t administration
