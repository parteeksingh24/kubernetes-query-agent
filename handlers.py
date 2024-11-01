"""
This file defines the query handlers for interacting with Kubernetes resources.
"""

from typing import Protocol, Dict, Any
import logging
from clients import core_v1_api, apps_v1_api
from helpers import simplify_name

# TODO: add more error logging here?

# Protocol for query handlers
class QueryHandler(Protocol):
    def handle(self, parameters: Dict[str, Any]) -> str:
        pass

# Query handler implementations:
class CountPodsHandler:
    """
    Handles queries that involve counting the number of pods in a given namespace.
    If no namespace is provided, it defaults to the 'default' namespace.
    """
    def handle(self, parameters: Dict[str, Any]) -> str:
        namespace = parameters.get('namespace', 'default')
        # Fetch pods in the namespace
        pods = core_v1_api.list_namespaced_pod(namespace=namespace)
        return str(len(pods.items))

class PodStatusHandler:
    """
    Handles queries that request the status of a specific pod.
    Requires `pod_name` to be provided. If no namespace is provided, it defaults to 'default'.
    """
    def handle(self, parameters: Dict[str, Any]) -> str:
        pod_name = parameters.get('pod_name') # Pod name must be specified
        if not pod_name:
            raise ValueError("Pod name required")
        namespace = parameters.get('namespace', 'default')
        # Fetch the pod details
        pod = core_v1_api.read_namespaced_pod(pod_name, namespace)
        # Return the pod's current status (e.g., Running, Pending)
        return pod.status.phase

class CountNodesHandler:
    """
    Handles queries that count the number of nodes in the Kubernetes cluster.
    """
    def handle(self, parameters: Dict[str, Any]) -> str:
        # Fetch all nodes in the cluster
        nodes = core_v1_api.list_node()
        # Return the count of nodes
        return str(len(nodes.items))

class DeploymentPodsHandler:
    """
    Handles queries that list pods created by a specific deployment.
    Requires `deployment_name` to be provided. Defaults to 'default' namespace if none is provided.
    """
    def handle(self, parameters: Dict[str, Any]) -> str:
        deployment_name = parameters.get('deployment_name') # Deployment name must be specified
        if not deployment_name:
            raise ValueError("Deployment name required")
        namespace = parameters.get('namespace', 'default')
        
        # Fetch deployment details
        deployment = apps_v1_api.read_namespaced_deployment(deployment_name, namespace)
        # Extract label selectors for the deployment
        selector = deployment.spec.selector.match_labels
        # Convert selectors into a query string
        label_selector = ','.join(f"{k}={v}" for k, v in selector.items())
        
        # Fetch pods matching the deployment
        pods = core_v1_api.list_namespaced_pod(namespace=namespace, label_selector=label_selector)
        if not pods.items:
            return ""
        # Simplify the returning pod name
        return simplify_name(pods.items[0].metadata.name)

class ServicePortHandler:
    """
    Handles queries that request the port number of a service.
    Requires `service_name` to be provided. Defaults to 'default' namespace if none is provided.
    """
    def handle(self, parameters: Dict[str, Any]) -> str:
        service_name = parameters.get('service_name') # Service name must be specified
        if not service_name:
            raise ValueError("Service name required")
        namespace = parameters.get('namespace', 'default')
        
        service = core_v1_api.read_namespaced_service(service_name, namespace) # Fetches service details
        if not service.spec.ports:
            return ""
        return str(service.spec.ports[0].port) # Returns the first port in the service spec

class DeploymentReplicasHandler:
    """
    Handles queries that request the number of replicas in a deployment.
    Requires `deployment_name` to be provided. Defaults to 'default' namespace if none is provided.
    """
    def handle(self, parameters: Dict[str, Any]) -> str:
        deployment_name = parameters.get('deployment_name') # Deployment name must be specified
        if not deployment_name:
            raise ValueError("Deployment name required")
        namespace = parameters.get('namespace', 'default')
        
        deployment = apps_v1_api.read_namespaced_deployment(deployment_name, namespace) # Fetches deployment details
        return str(deployment.spec.replicas) # Returns the configured number of replicas

class PodContainersHandler:
    """
    Handles queries that list the container names within a pod.
    Requires `pod_name` to be provided. Defaults to 'default' namespace if none is provided.
    """
    def handle(self, parameters: Dict[str, Any]) -> str:
        pod_name = parameters.get('pod_name') # Pod name must be specified
        if not pod_name:
            raise ValueError("Pod name required")
        namespace = parameters.get('namespace', 'default') # Default to 'default' namespace
        
        # Fetch the pod details
        pod = core_v1_api.read_namespaced_pod(pod_name, namespace)
        
        # Extract container image names (without tag)
        containers = []
        for container in pod.spec.containers:
            image = container.image.split(':')[0] # Remove tag if present
            if '/' in image:
                image = image.split('/')[-1] # Get just the image name without registry
            containers.append(image)
        
        return ",".join(containers)

class ServiceTypeHandler:
    """
    Handles queries that request the type of a service (e.g., ClusterIP, NodePort, LoadBalancer).
    Requires `service_name` to be provided. Defaults to 'default' namespace if none is provided.
    """
    def handle(self, parameters: Dict[str, Any]) -> str:
        service_name = parameters.get('service_name') # Service name must be specified
        if not service_name:
            raise ValueError("Service name required")
        namespace = parameters.get('namespace', 'default')
        
        service = core_v1_api.read_namespaced_service(service_name, namespace) # Fetches service details
        return service.spec.type # Returns the service type

class PodNamespaceHandler:
    """
    Handles queries that request the namespace of a specific pod.
    Requires `pod_name` to be provided.
    """
    def handle(self, parameters: Dict[str, Any]) -> str:
        pod_name = parameters.get('pod_name') # Pod name must be specified
        if not pod_name:
            raise ValueError("Pod name required")
        
        pods = core_v1_api.list_pod_for_all_namespaces() # Fetches all pods across all namespaces
        for pod in pods.items:
            if pod.metadata.name == pod_name:
                return pod.metadata.namespace # Returns the namespace if the pod is found
        return "not found" # Pod is not present in any namespace

class ListNamespacesHandler:
    """
    Handles queries that list all namespaces in the Kubernetes cluster.
    """
    def handle(self, parameters: Dict[str, Any]) -> str:
        namespaces = core_v1_api.list_namespace() # Fetches all namespaces
        namespace_names = [ns.metadata.name for ns in namespaces.items] # Extracts namespace names
        return ",".join(namespace_names) # Returns the namespace names as a comma-separated string

class NodeStatusHandler:
    """
    Handles queries that request the status of a specific node.
    Requires `node_name` to be provided.
    """
    def handle(self, parameters: Dict[str, Any]) -> str:
        node_name = parameters.get('node_name') # Node name must be specified
        if not node_name:
            raise ValueError("Node name required")
        
        node = core_v1_api.read_node(node_name) # Fetches node details
        for condition in node.status.conditions:
            if condition.type == 'Ready': # Looks for the 'Ready' condition
                return condition.status # Returns the status of the node (e.g., True, False)
        return "Unknown" # Status could not be determined

class ListServicesHandler:
    """
    Handles queries that list all services in a specified namespace.
    Defaults to 'default' namespace if none is provided.
    """
    def handle(self, parameters: Dict[str, Any]) -> str:
        namespace = parameters.get('namespace', 'default') # Defaults to 'default' if no namespace provided
        services = core_v1_api.list_namespaced_service(namespace) # Fetches all services in the namespace
        service_names = [simplify_name(svc.metadata.name) for svc in services.items] # Extracts service names
        return ",".join(service_names) # Returns the service names as a comma-separated string

class PodLogsHandler:
    """
    Handles queries that request the recent logs of a specific pod.
    Requires `pod_name` to be provided. Defaults to 'default' namespace if none is provided.
    Limits the logs to the last 10 lines by default.
    """
    def handle(self, parameters: Dict[str, Any]) -> str:
        pod_name = parameters.get('pod_name') # Pod name must be specified
        if not pod_name:
            raise ValueError("Pod name required")
        namespace = parameters.get('namespace', 'default') # Default to 'default' namespace
        
        try:
            # Fetch the last 10 lines of the pod's logs
            logs = core_v1_api.read_namespaced_pod_log(
                pod_name, 
                namespace,
                tail_lines=10 # Limit to the last 10 lines of logs
            )
            return logs.strip() # Return the logs (stripped of leading/trailing whitespace)
        except Exception as e:
            logging.error(f"Error getting pod logs: {e}") # Log any errors encountered
            return "No logs available" # Return a fallback message if logs can't be retrieved

class ResourceUsageHandler:
    """
    Handles queries that request the resource usage/requests for a specific pod.
    Requires `pod_name` to be provided. Defaults to 'default' namespace if none is provided.
    Returns the CPU and memory requests for the pod's first container.
    """
    def handle(self, parameters: Dict[str, Any]) -> str:
        pod_name = parameters.get('pod_name') # Pod name must be specified
        if not pod_name:
            raise ValueError("Pod name required")
        namespace = parameters.get('namespace', 'default') # Default to 'default' namespace
        
        # Fetch the pod details
        pod = core_v1_api.read_namespaced_pod(pod_name, namespace)
        # Get resource requests for the first container in the pod
        resources = pod.spec.containers[0].resources
        if resources and resources.requests:
            # Get CPU and memory requests, or 'none' if not specified
            cpu = resources.requests.get('cpu', 'none')
            memory = resources.requests.get('memory', 'none')
            return f"CPU: {cpu}, Memory: {memory}" # Return CPU and memory requests
        return "No resource requests specified" # Fallback message if no resources are specified

# Query handler registry:
# (maps query types to their corresponding handler classes for easy extensibility)
QUERY_HANDLERS = {
    "count_pods": CountPodsHandler(),
    "pod_status": PodStatusHandler(),
    "count_nodes": CountNodesHandler(),
    "deployment_pods": DeploymentPodsHandler(),
    "service_port": ServicePortHandler(),
    "deployment_replicas": DeploymentReplicasHandler(),
    "pod_containers": PodContainersHandler(),
    "service_type": ServiceTypeHandler(),
    "pod_namespace": PodNamespaceHandler(),
    "list_namespaces": ListNamespacesHandler(),
    "node_status": NodeStatusHandler(),
    "list_services": ListServicesHandler(),
    "pod_logs": PodLogsHandler(),
    "resource_usage": ResourceUsageHandler(),
}
