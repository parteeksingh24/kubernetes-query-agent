"""
Kubernetes Query Agent

A FastAPI-based AI agent that answers queries about applications
deployed on a Kubernetes cluster.

This script implements the core API endpoint and service structure.
"""

import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ValidationError
from clients import verify_clients
from handlers import QUERY_HANDLERS
from utils import classify_query, get_kubernetes_info

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

# Define question (query), answer (response) structure
# (Pydantic BaseModel -- automatic data validation)
class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    query: str
    answer: str

# Verify clients before serving requests
try:
    verify_clients()
    logging.debug("All clients successfully verified.")
except Exception as e:
    logging.error(f"Failed to verify clients: {e}")
    raise SystemExit("Failed to verify required clients.")

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
        logging.debug(f"Processing query: {request.query}")

        # Classify query using GPT-4o-mini
        classification = classify_query(request.query)

        # Get info. from Kubernetes
        answer = get_kubernetes_info(
            classification['type'],
            classification.get('parameters', {})
        )

        # Log the response
        logging.debug(f"Query response: {answer}")

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
    logging.debug("Initializing Query Agent")
    logging.debug(f"Registered handlers: {', '.join(QUERY_HANDLERS.keys())}")
    
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
            "main:app", # Use string reference to app
            host="127.0.0.1",
            port=port,
            log_level="info"
        )
    except Exception as e:
        logging.error(f"Failed to start server: {e}")
        sys.exit(1)
