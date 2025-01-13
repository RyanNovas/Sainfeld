#!/bin/bash

# Create the static directory
mkdir -p static

# Add a .gitkeep file to ensure the directory is tracked by Git
touch static/.gitkeep

echo "Static directory created successfully."