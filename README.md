# Kubernetes Query Agent

A FastAPI-based AI agent that answers queries about applications deployed on a Kubernetes cluster.

## Table of Contents

1. [Introduction](#introduction)
2. [Features](#features)
3. [Architecture](#architecture)
4. [Installation](#installation)
5. [Usage](#usage)
6. [Troubleshooting Tips](#troubleshooting-tips)
7. [License](#license)

## Introduction

The Kubernetes Query Agent is a basic tool designed to make understanding Kubernetes cluster resources simple and efficient. By leveraging natural language processing (NLP) with GPT-4o-mini, this application **classifies and processes user queries**, automatically retrieving the relevant information from your Kubernetes environment.

Developed as part of the *Cleric Query Agent Assignment*, this Python-based application provides a RESTful API, built with FastAPI and Pydantic, that interprets and responds to user requests.

### How It Works

The Query Agent follows a three-step process, done in succession to process user queries:
1. GPT-4o-mini performs **query classification** by determining the *query type* (one of 14 accepted queries) and **extracts parameters** related to that query.
    - For example, if a user asks about the status of `example-pod`, the main extracted parameter would be `pod_name=example-pod`.
2. Using the query type and corresponding parameters, the application calls the corresponding Kubernetes API function to retrieve the desired information.
3. Finally, the application returns a *simplified* version of the API output.
    - For example, this step would simplify `my-deployment-56c598c8fc` to `my-deployment`, with hash suffixes removed.

As a result, the *Kubernetes Query Agent* performs **read-only** actions on the Kubernetes cluster.

## Features

- *Query Classification*: The agent uses NLP to classify user queries into predefined types, such as "count_pods", "pod_status", "count_nodes", etc.
- *Kubernetes Integration*: The agent interacts with the Kubernetes API to fetch information about deployed resources, including pods, deployments, services, and nodes.
- *Error Handling*: The agent provides clear error messages for various types of errors, including validation errors, Kubernetes API errors, and unexpected exceptions.
- *Logging*: The agent logs important events, including incoming queries, classification results, and API responses, to the `agent.log` file for debugging and monitoring purposes.

## Architecture

### Key Components

1. FastAPI Application (`main.py`): The main entry point of the application, handling incoming HTTP requests and responses.
2. Query Classifier (`utils.py`): Responsible for analyzing user queries and classifying them into predefined types using natural language processing.
3. Kubernetes Client (`clients.py`): Provides a wrapper around the Kubernetes Python client, allowing the agent to interact with the Kubernetes API.
4. Query Handlers (`handlers.py`): Implement the logic to fetch and process information from the Kubernetes cluster for each query type.
5. Utilities (`utils.py`): Helper functions for tasks such as Kubernetes resource name simplification and returning Kubernetes cluster information.

### Scope of Queries

The agent is capable of handling the following types of queries:
1. `count_pods`: Count pods in a namespace
2. `pod_status`: Get status of a specific pod
3. `count_nodes`: Count cluster nodes
4. `deployment_pods`: Get pods from a deployment
5. `service_port`: Get port of a service
6. `deployment_replicas`: Get replica count of deployment
7. `pod_containers`: List containers in a pod
8. `service_type`: Get service type
9. `pod_namespace`: Get namespace of a pod
10. `list_namespaces`: List all namespaces
11. `node_status`: Get status of a specific node
12. `list_services`: List services in a namespace
13. `pod_logs`: Get recent logs from a pod
14. `resource_usage`: Get resource usage/requests for a pod

### Technical Implementation

To *handle* the 14 accepted queries in a modular way, each query is related to its own handler class. These *handlers* call their respective Kubernetes API function.

The `QUERY_HANDLERS` dictionary links these query types with their associated handler class, as shown below:

```
# Handler Protocol
class QueryHandler(Protocol):
    def handle(self, parameters: Dict[str, Any]) -> str:
        pass

# Handler Registry
QUERY_HANDLERS = {
    "count_pods": CountPodsHandler(),
    "pod_status": PodStatusHandler(),
    "count_nodes": CountNodesHandler(),
    "deployment_pods": DeploymentPodsHandler(),
    # ... additional handlers
}
```

From here, the `get_kubernetes_info` function uses the given `query_type` to look up the appropriate handler. It executes this handler with the necessary parameters, and returns a formatted response. This structure effectively *delegates the query processing* to each specific type of question asked:

```
def get_kubernetes_info(query_type: str, parameters: dict) -> str:
    # Get the appropriate handler for this query type from the registry
    handler = QUERY_HANDLERS.get(query_type)
    if not handler:
        raise ValueError(f"Unsupported query type: {query_type}")
        
    # Delegate the actual query processing to the specific handler
    return handler.handle(parameters)
```

Putting all of this together, the `process_query` function will classify the incoming query, then call the `get_kubernetes_info` function to invoke the correct Kubernetes API function for that query:

```
def process_query(request: QueryRequest):
    # Classify query using GPT-4o-mini
    classification = classify_query(request.query)

    # Get info. from Kubernetes
    answer = get_kubernetes_info(
        classification['type'],
        classification.get('parameters', {})
    )

    # Return using the specified response model/format
    return QueryResponse(query=request.query, answer=answer)
```

## Installation

### Prerequisites

Before you begin, ensure you have the following installed:
- **Python 3.10+**: Make sure Python is installed and accessible from your command line.
- **[Minikube](https://minikube.sigs.k8s.io/docs/start/)**: A tool that runs a single-node Kubernetes cluster locally, perfect for testing the Query Agent.
- **[kubectl](https://kubernetes.io/docs/tasks/tools/)**: The official Kubernetes CLI tool for interacting with and managing Kubernetes clusters.
- **[Docker](https://docs.docker.com/get-docker/)**: A platform for developing, shipping, and running containerized applications. Required by Minikube.
- **Virtual Environment**: A suggested approach to isolate project dependencies from other Python projects and system packages.

You'll also need:
- An **[OpenAI API](https://platform.openai.com/) key** with sufficient credits for query classification.

### Setup

1. Clone the repository:
```
git clone https://github.com/parteeksingh24/kubernetes-query-agent.git
cd kubernetes-query-agent
```

2. Create and activate a virtual environment:
```
python3.10 -m venv venv
source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
```

3. Install dependencies:
```
pip install -r requirements.txt
```

4. Configure environment variables:
Create an `.env` file in the root directory and add your OpenAI API key:
```
OPENAI_API_KEY=your-openai-api-key
```

## Usage

### Running the Agent

1. Start Minikube:
```
minikube start
```

2. Deploy sample applications:
Use `kubectl` (e.g., create deployments, run pods) to test queries. For example:
```
kubectl create deployment example-pod --image=nginx
```
This creates a simple Nginx pod in the default namespace.

3. Start the FastAPI server:
There are various ways to run the Query Agent, but the simplest is:
```
python main.py
```
The server will start running on http://localhost:8000.

### Interacting with the Agent

You can interact with the agent using a tool like curl or a web browser. The following shows how to use `curl` on the command line.

1. Submit a query
To interact with the Kubernetes Query Agent, send a POST request to the `/query` endpoint. For example:
```
curl -X POST "http://localhost:8000/query" \
-H "Content-Type: application/json" \
-d '{"query": "How many pods are in the default namespace?"}'
```

2. The agent will respond with the answer:
```
{
    "query": "How many pods are in the default namespace?",
    "answer": "1"
}
```

### Logging

Logs are written to `agent.log` for debugging and monitoring query processing.

## Troubleshooting Tips

1. *Connection Issues*: Ensure Minikube is running and your kubeconfig is correctly set up:
```
minikube start
minikube status  # Should show "Running"
kubectl cluster-info  # Should show cluster information
```
Be sure to check that the Kubernetes configuration file is located at `~/.kube/config`.

2. Ensure the *FastAPI service* is running (via the command line):
```
curl -X POST "http://localhost:8000/health"
```

3. *API Key errors*: Verify your OpenAI API key is correctly configured in the `.env` file.
4. *Check logs*: Review the `agent.log` file to help diagnose issues if they persist. 

## License

This project is licensed under the MIT License.
