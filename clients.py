"""
This file sets up the necessary API (Kubernetes, OpenAI) clients.
"""

import os
import logging
from kubernetes import client, config
from openai import OpenAI
from dotenv import load_dotenv

# Load API key for OpenAI model usage
load_dotenv()

# Initialize Kubernetes API clients at module level
try:
    config.load_kube_config()
    core_v1_api = client.CoreV1Api()
    apps_v1_api = client.AppsV1Api()
    
    # Test connection
    core_v1_api.list_node()
    logging.debug("Successfully initialized Kubernetes clients")
except Exception as e:
    logging.error(f"Failed to initialize Kubernetes clients: {e}")
    core_v1_api = None
    apps_v1_api = None

# Initialize OpenAI client at module level
try:
    openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
    logging.debug("Successfully initialized OpenAI client")
except Exception as e:
    logging.error(f"Failed to initialize OpenAI client: {e}")
    openai_client = None

def verify_clients():
    """
    Verify that both OpenAI and Kubernetes clients are properly initialized.
    """
    if not openai_client:
        raise SystemExit("OpenAI client is not initialized")
    if not core_v1_api or not apps_v1_api:
        raise SystemExit("Kubernetes clients are not initialized")
    logging.debug("All clients successfully verified")
