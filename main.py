"""
Kubernetes Query Agent

A FastAPI-based AI agent that answers queries about applications
deployed on a Kubernetes cluster.

This script implements the core API endpoint and service structure.
"""

import os
import logging
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ValidationError
from kubernetes import client, config
from openai import OpenAI

# Logging configuration:
# - DEBUG level captures more detailed information
# - filemode='a' ensures logs are appended, not overwritten
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s - %(message)s',
    filename='agent.log',
    filemode='a'
)

# Initialize FastAPI app (for automatic data validation compared to Flask)
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
def get_openai_key() -> str:
    """
    Get OpenAI API key from environment variable.
    Ensures that the key used is not hard-coded into the script.
    """
    # TODO: would using `python-dotenv` be better here?

    key = os.getenv('OPENAI_API_KEY')
    if not key:
        error_msg = "OPENAI_API_KEY environment variable not set"
        logging.error(error_msg)
        raise EnvironmentError(error_msg)
    return key

def load_kubernetes_config() -> bool:
    """
    Load Kubernetes configuration from the default location (~/.kube/config).
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

        # Verify cluster is available (by listing current nodes)
        core_v1_api.list_node()
        logging.debug("Successfully connected to Kubernetes cluster")
        return True
    except Exception as e:
        logging.error(f"Failed to load Kubernetes config: {e}")
        return False

# After app initialization, initialize OpenAI client (only done once):
try:
    openai_client = OpenAI(api_key=get_openai_key())
    logging.info("Successfully initialized OpenAI client")
except Exception as e:
    # Terminate the program on failure
    logging.error(f"Failed to initialize OpenAI client: {e}")
    raise SystemExit("Failed to initialize OpenAI client")

# Use AI agent to extract info. (utilizing NLP) from a query:
def classify_query(query: str) -> dict:
    """
    Use GPT-4o-mini to classify the `query` type and extract relevant parameters.
    """
    # System prompt to guide the AI agent/assistant
    # TODO: add more classifications?
    system_prompt = """
    You are a Kubernetes query classification assistant that categorizes queries and extracts parameters. 
    Please follow the given instructions carefully, making sure to think through each major step before proceeding.

    TASK:
    Analyze the query and classify it into one of these types:
    1. "count_pods" - Count pods in a namespace (requires: none, optional: namespace [defaults to "default"])
    2. "pod_status" - Get status of a specific pod (requires: pod_name, optional: namespace [defaults to "default"])
    3. "count_nodes" - Count cluster nodes (requires: none, optional: none)
    4. "deployment_pods" - Get pods from a deployment (requires: deployment_name, optional: namespace [defaults to "default"])

    PARAMETERS TO EXTRACT:
    - namespace: Extract if specified, otherwise assume "default" for relevant queries
    - pod_name: Required for pod status queries
    - deployment_name: Required for deployment pod queries

    RULES:
    - Remove hash suffixes from names (e.g., "my-pod-12345" → "my-pod")
    - Omit parameters if not mentioned in query
    - Return only a JSON object with type and parameters
    - For unknown queries, return {"type": "unknown", "parameters": {}}
    - Always use "default" namespace if none specified

    OUTPUT FORMAT:
    You must return a valid JSON object with exactly this structure:
    {
        "type": string, // One of: "count_pods", "pod_status", "count_nodes", "deployment_pods", "unknown"
        "parameters": {
            // Only include relevant parameters, can be empty
            "namespace"?: string,        // Optional
            "pod_name"?: string,         // Optional
            "deployment_name"?: string   // Optional
        }
    }

    EXAMPLES:
    Query: "Which pod is spawned by my-deployment?"
    Response: {
        "type": "deployment_pods",
        "parameters": {
            "deployment_name": "my-deployment",
            "namespace": "default"
        }
    }

    Query: "What is the status of the pod named 'example-pod'?"
    Response: {
        "type": "pod_status",
        "parameters": {
            "pod_name": "example-pod",
            "namespace": "default"
        }
    }

    Query: "How many nodes are there in the cluster?"
    Response: {
        "type": "count_nodes",
        "parameters": {}
    }

    Query: "How many pods are in the default namespace?"
    Response: {
        "type": "count_pods",
        "parameters": {
            "namespace": "default"
        }
    }
    """
    
    try:
        logging.debug(f"Sending query to GPT-4o-mini: {query}")

        # Get a response from the AI model based on the system prompt and user query
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            temperature=0, # Get deterministic (consistent) responses for similar queries
            response_format={"type": "json_object"} # Extra validation
        )

        # Parse the (JSON) response from the model
        result=json.loads(response.choices[0].message.content)
        logging.debug(f"GPT-4o-mini classification result: {result}")
        return result
    except Exception as e:
        logging.error(f"Error in query classification: {e}")
        raise

# TODO: add a helper function to `get_kubernetes_info` based on given query
# TODO: implement API endpoint to process queries and return responses
#       (including validation and error handling for both request and response)

# Main entry point
if __name__ == "__main__":
    # TODO: Implement server startup using provided URL, port
    pass
