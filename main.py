"""
Kubernetes Query Agent

A FastAPI-based AI agent that answers queries about applications
deployed on a Kubernetes cluster.

This script implements the core API endpoint and service structure.
"""

import os
import logging
import json
from typing import Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ValidationError
from kubernetes import client, config
import openai

# Logging configuration:
# - DEBUG level captures more detailed information
# - filemode='a' ensures logs are appended, not overwritten
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s - %(message)s',
    filename='agent.log',
    filemode='a'
)

# Initialize FastAPI app (for async, automatic data validation compared to Flask)
app = FastAPI()

# Kubernetes API clients (initialized in `load_kubernetes_config`)
core_v1_api = None
apps_v1_api = None

# Define question (query), answer (response) structure
# (Pydantic BaseModel -- automatic data validation)
class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    query: str
    answer: str

# Helper functions:
def load_kubernetes_config() -> bool:
    """
    Load Kubernetes configuration from ~/.kube/config.
    Returns `True` if successful, `False` otherwise.
    """
    global core_v1_api, apps_v1_api

    # Check full path for configuration details
    config_path = os.path.expanduser('~/.kube/config')
    if not os.path.exists(config_path):
        logging.error("Kubernetes config file not found at ~/.kube/config")
        return False

    try:
        # Load the Kubernetes config, init API clients
        config.load_kube_config()
        core_v1_api = client.CoreV1Api()
        apps_v1_api = client.AppsV1Api()

        # Verify cluster is available by listing current nodes
        core_v1_api.list_node()
        logging.debug("Successfully connected to Kubernetes cluster")
        return True
    except Exception as e:
        logging.error(f"Failed to load Kubernetes config: {e}")
        return False

def get_openai_key() -> str:
    """
    Get OpenAI API key from environment variable.
    Ensures that the key used is not hard-coded into the script.
    """
    key = os.getenv('OPENAI_API_KEY')
    if not key:
        error_msg = "OPENAI_API_KEY environment variable not set"
        logging.error(error_msg)
        raise EnvironmentError(error_msg)
    return key

# TODO: process queries using GPT-4, add a helper function to `get_kubernetes_info`
# TODO: handle queries and return responses (including error checking+handling)

# Main entry point
if __name__ == "__main__":
    # TODO: Implement server startup using provided URL, port
    pass
