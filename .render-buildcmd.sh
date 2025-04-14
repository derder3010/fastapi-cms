#!/bin/bash

# Enable core.longpaths in git to handle long filenames
git config --global core.longpaths true

# Continue with regular build commands
if [ -f requirements.txt ]; then
    pip install -r requirements.txt
fi

# Run any other build commands needed
python -m app.main 