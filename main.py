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
# (type hints ensure API functions are visible)
core_v1_api: client.CoreV1Api
apps_v1_api: client.AppsV1Api

# Define question (query), answer (response) structure
# (Pydantic BaseModel -- automatic data validation)
class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    query: str
    answer: str

# Helper function to retrieve the OpenAI API key:
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

# Helper function to load Kubernetes configuration:
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

# Function to initialize OpenAI and Kubernetes clients:
def initialize_clients():
    """
    Initialize OpenAI and Kubernetes clients.
    """
    global openai_client, core_v1_api, apps_v1_api

    # Initialize OpenAI client
    try:
        openai_client = OpenAI(api_key=get_openai_key())
        logging.info("Successfully initialized OpenAI client")
    except Exception as e:
        logging.error(f"Failed to initialize OpenAI client: {e}")
        raise SystemExit("Failed to initialize OpenAI client")

    # Initialize Kubernetes configuration
    if not load_kubernetes_config():
        raise SystemExit("Failed to initialize Kubernetes configuration")

# Perform client initialization before serving requests
initialize_clients()

# Helper function to simplify Kubernetes resource names:
def simplify_name(full_name: str) -> str:
    """
    Simplifies a Kubernetes resource name by removing hash-like suffixes.
    
    Following Kubernetes naming conventions, this function identifies and removes
    hash suffixes that are commonly added to resource names (like ReplicaSets
    and Pods). These hashes are typically 5-10 characters long and contain at
    least one digit.
    
    Args:
        `full_name`: The complete Kubernetes resource name
        
    Returns:
        The simplified name with hash suffixes removed
        
    Examples:
        - 'nginx-deployment-5959b5b5c9-fdtrb' -> 'nginx-deployment'
        - 'example-pod' -> 'example-pod'
        - 'mongodb-56c598c8fc' -> 'mongodb'
        - 'my-deployment-577d9fbfb9-z8246' -> 'my-deployment'
    """
    # Constants defining typical hash suffix lengths
    MIN_HASH_LENGTH = 5
    MAX_HASH_LENGTH = 10
    
    # Split resource name into parts (using hyphens as delimiter)
    parts = full_name.split('-')
    simplified = []

    for part in parts:
        # Stop if the part matches hash pattern (5-10 chars, contains digit)
        is_hash = (MIN_HASH_LENGTH <= len(part) <= MAX_HASH_LENGTH and 
                  any(char.isdigit() for char in part))
        
        if is_hash:
            break
    
        simplified.append(part)

    # Join the valid (non-hash) segments for the simplified name
    return '-'.join(simplified)

# Use AI agent to extract info. (utilizing NLP) from a query:
def classify_query(query: str) -> dict:
    """
    Use GPT-4o-mini to classify the `query` type and extract relevant parameters.
    """
    # System prompt to guide the AI agent/assistant
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

# Health check endpoint: verify FastAPI is running
@app.get("/health")
def health_check():
    return {"status": "healthy"}

# API (POST) endpoint (to process queries, return responses):
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

# Main entry point
if __name__ == "__main__":
    import sys
    import uvicorn
    
    # Configure logging
    logging.info("Starting server...")
    
    # Get port from command line args or use default
    port = 8000
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            logging.error(f"Invalid port number: {sys.argv[1]}")
            sys.exit(1)
    
    # Start server
    try:
        uvicorn.run(
            "main:app",  # Use string reference to app
            host="127.0.0.1",
            port=port,
            log_level="info"
        )
    except Exception as e:
        logging.error(f"Failed to start server: {e}")
        sys.exit(1)
