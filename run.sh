#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# Run the FastAPI app
uvicorn main:app --reload