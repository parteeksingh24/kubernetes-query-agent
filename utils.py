"""
Utility functions for Kubernetes resource name simplification and AI query classification.
"""

import logging
import json
from kubernetes import client
from clients import openai_client
from handlers import QUERY_HANDLERS

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
    1. "count_pods" - Count pods in a namespace (optional: namespace)
    2. "pod_status" - Get status of a specific pod (requires: pod_name, optional: namespace)
    3. "count_nodes" - Count cluster nodes
    4. "deployment_pods" - Get pods from a deployment (requires: deployment_name, optional: namespace)
    5. "service_port" - Get port of a service (requires: service_name, optional: namespace)
    6. "deployment_replicas" - Get replica count of deployment (requires: deployment_name, optional: namespace)
    7. "pod_containers" - List containers in a pod (requires: pod_name, optional: namespace)
    8. "service_type" - Get service type (requires: service_name, optional: namespace)
    9. "pod_namespace" - Get namespace of a pod (requires: pod_name)
    10. "list_namespaces" - List all namespaces
    11. "node_status" - Get status of a specific node (requires: node_name)
    12. "list_services" - List services in a namespace (optional: namespace)
    13. "pod_logs" - Get recent logs from a pod (requires: pod_name, optional: namespace)
    14. "resource_usage" - Get resource usage/requests for a pod (requires: pod_name, optional: namespace)

    PARAMETERS TO EXTRACT:
    - namespace: Optional, defaults to "default"
    - pod_name: Required for pod-related queries
    - deployment_name: Required for deployment queries
    - service_name: Required for service queries
    - node_name: Required for node queries

    RULES:
    - Omit parameters if not mentioned in query
    - Return only a JSON object with type and parameters
    - For unknown queries, return {"type": "unknown", "parameters": {}}
    - Always use "default" namespace if none specified

    OUTPUT FORMAT:
    You must return a valid JSON object with exactly this structure:
    {
        "type": string, // Must correspond to one of the query types described in the TASK section (e.g., "count_pods", "pod_status", etc.)
        "parameters": {
            "namespace": string (optional, defaults to "default"),
            "pod_name": string (required for pod-related queries),
            "deployment_name": string (required for deployment-related queries),
            "service_name": string (required for service-related queries),
            "node_name": string (required for node-related queries)
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
        logging.debug(f"Classifying query: {query}")

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
        logging.debug(f"Classification result: {result['type']}")
        return result
    except Exception as e:
        logging.error(f"Error in query classification: {e}")
        raise

# Get Kubernetes info. based on query:
def get_kubernetes_info(query_type: str, parameters: dict) -> str:
    """
    Get information from Kubernetes based on query type and parameters.
    Uses the handler pattern to process different query types.
    """
    try:
        logging.debug(f"Processing query type: {query_type} with parameters: {parameters}")
        
        # Get the appropriate handler for this query type from the registry
        handler = QUERY_HANDLERS.get(query_type)
        if not handler:
            raise ValueError(f"Unsupported query type: {query_type}")
            
        # Delegate the actual query processing to the specific handler
        return handler.handle(parameters)
        
    except client.rest.ApiException as e:
        # Handle Kubernetes API-specific errors
        logging.error(f"Kubernetes API error: {e}")
        if e.status == 404:
            return "Not found"
        raise
    except Exception as e:
        # Catch and log any other unexpected errors
        logging.error(f"Error processing query: {e}")
        raise
