"""
Kubernetes Query Agent

A FastAPI-based AI agent that answers queries about applications
deployed on a Kubernetes cluster.

This script implements the core API endpoint and service structure.
"""


# TODO: extend the agent beyond just a few classifications?
#       (maybe just add "service status"?)


import os
import logging
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ValidationError
from kubernetes import client, config
from openai import OpenAI
from dotenv import load_dotenv

# Logging configuration:
# - DEBUG level captures more detailed information
# - filemode='a' ensures logs are appended, not overwritten
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s - %(message)s',
    filename='agent.log',
    filemode='a'
)

# Load API key for OpenAI model usage
load_dotenv()

# Initialize FastAPI app (for automatic data validation compared to Flask)
app = FastAPI()

# Kubernetes API clients (initialized in `load_kubernetes_config`)
# (type hints ensure Kubernetes API functions are visible)
core_v1_api: client.CoreV1Api
apps_v1_api: client.AppsV1Api

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
    
def simplify_name(full_name: str) -> str:
    """
    Simplify Kubernetes information by removing hash suffixes while preserving the core name.
    
    Examples:
        'mongodb-56c598c8fc' -> 'mongodb'.

        'my-deployment-577d9fbfb9-z8246' -> 'my-deployment'.

        'example-pod' -> 'example-pod'.
    """
    # Split incoming name by hyphen
    parts = full_name.split('-')
    
    # Define possible hash lengths (based on Kubernetes API)
    HASH_LENGTHS = {5, 10} # For DaemonSet and ReplicaSet (deployment)
    
    # Continuously remove suffixes that match hash patterns
    while parts:
        last_part = parts[-1]
        if len(last_part) in HASH_LENGTHS and last_part.isalnum():
            parts.pop()
        else:
            break # Only valid `parts` of the name remain
    
    simplified_name = '-'.join(parts)
    
    # Ensure that if all parts were removed, we just return the original name
    return simplified_name if simplified_name else full_name

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

# Get Kubernetes info. based on query:
def get_kubernetes_info(query_type: str, parameters: dict) -> str:
    """
    Get information from Kubernetes based on `query_type` and `parameters` given.
    Returns simplified answers without identifiers.
    """
    try:
        logging.debug(f"Processing query type: {query_type} with parameters: {parameters}")

        if query_type == "count_pods":
            # List all pods in the given `namespace` (default = `default`)
            namespace = parameters.get('namespace', 'default')
            pods = core_v1_api.list_namespaced_pod(namespace=namespace)
            return str(len(pods.items))

        elif query_type == "pod_status":
            # Extract the `pod_name`, or raise an error if not found
            pod_name = parameters.get('pod_name')
            if not pod_name:
                raise ValueError("Pod name not found in query")
            
            # Get pod details from the "default" namespace
            pod = core_v1_api.read_namespaced_pod(pod_name, "default")

            # Return the pod's status (e.g., Running, Pending)
            return pod.status.phase
        
        elif query_type == "count_nodes":
            # List all nodes in the Kubernetes cluster
            nodes = core_v1_api.list_node()
            return str(len(nodes.items))
        
        elif query_type == "deployment_pods":
            # Extract the `deployment_name`, or raise an error if not found
            deployment_name = parameters.get('deployment_name')
            if not deployment_name:
                raise ValueError("Deployment name not found in query")
            
            # Get deployment details from the "default" namespace
            deployment = apps_v1_api.read_namespaced_deployment(deployment_name, "default")
            # Extract the label selectors used by the deployment
            selector = deployment.spec.selector.match_labels
            # Convert the label selectors to a comma-separated string for filtering pods
            label_selector = ','.join(f"{k}={v}" for k, v in selector.items())

            # List all pods that match deployment's label selector
            pods = core_v1_api.list_namespaced_pod(namespace="default", label_selector=label_selector)
            if not pods.items:
                return ""
            
            # Extract (and simplify) the first pod name
            pod_name = pods.items[0].metadata.name
            simplified_name = simplify_name(pod_name)
            logging.debug(f"Simplified pod name from {pod_name} to {simplified_name}")
            return simplified_name

        else:
            raise ValueError(f"Unsupported query type: {query_type}")
    except client.rest.ApiException as e:
        logging.error(f"Kubernetes API error: {e}")
        if e.status == 404:
            return "Not found"
        # Re-raise the exception for other types of API errors
        raise
    # Handle other exceptions that may occur during query processing
    except Exception as e:
        logging.error(f"Error processing query: {e}")
        raise

# API (POST) endpoint (to process queries, return responses)
#   (includes validation and error handling for both request and response)
@app.post("/query", response_model=QueryResponse)
def process_query(request: QueryRequest):
    """
    Handle incoming queries (`request`) and return responses.
    Returns only the answer without additional context.
    """
    try:
        # Log incoming query
        logging.debug(f"Received query: {request.query}")

        # Classify query using GPT-4o-mini
        classification = classify_query(request.query)

        # Get info. from Kubernetes
        answer = get_kubernetes_info(
            classification['type'],
            classification.get('parameters', {})
        )

        # Log the response
        logging.debug(f"Responding with answer: {answer}")

        # Return using the specified response model/format
        return QueryResponse(query=request.query, answer=answer)
    except ValidationError as e:
        # Handle validation errors
        logging.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=e.errors())
    except ValueError as e:
        # Handle invalid queries
        logging.error(f"Invalid query: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        # General error handling
        logging.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Initialize Kubernetes configuration
if not load_kubernetes_config():
    raise SystemExit("Failed to initialize Kubernetes configuration")

# Main entry point
if __name__ == "__main__":
    # Start the server using provided URL, port
    import uvicorn
    logging.info("Starting server...")
    uvicorn.run(app, host="127.0.0.1", port=8000)
