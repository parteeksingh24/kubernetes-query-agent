# Kubernetes Query Agent

An AI agent that **answers queries about applications deployed on a Kubernetes cluster**, using GPT-4o-mini for query processing and FastAPI for API endpoints with Pydantic support and built-in validation.

## Overview
This agent provides a REST API endpoint that processes queries about Kubernetes cluster state and returns simplified answers. It does so by performing the following tasks:

1. Processes natural language queries using GPT-4o-mini to classify and understand user intent.
2. Based on the information extracted by the model, returns the (simplified) relevant info. from a Kubernetes cluster using the Kubernetes API.

As a result, the *Kubernetes Query Agent* performs **read-only** actions on the Kubernetes cluster.

## About
This project was developed as part of the Cleric Query Agent Assignment.

## Setup
Instructions coming soon.

## Usage
Documentation coming soon.

## Changelog

### [Unreleased]
#### Added
- Load OpenAI API key using `load_dotenv` and an `.env` file.
- Fixed error that initialized Kubernetes API clients to `None` throughout the script.
- Name simplification function (`simplify_name`) to remove hash suffixes from Kubernetes resource names.
- Updated query processing model to **not** simplify names by removing hash suffixes (now done by `get_kubernetes_info`).
- Helper function (`get_kubernetes_info`) to retrieve information based on the classified query.
- Query processing and response generation (including error checking and handling).
- Server startup configuration in `main`.

#### TODO
- Add input validation and expand error handling.
- Extend functionality beyond the current query classifications (*if needed*).
- Add setup instructions and usage documentation.
