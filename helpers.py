"""
This file defines common functions used across multiple modules.
"""

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
