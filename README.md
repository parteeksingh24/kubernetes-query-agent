# Kubernetes Query Agent

An AI agent that **answers queries about applications deployed on a Kubernetes cluster**, using GPT-4o-mini for query processing and FastAPI for API endpoints with Pydantic support and built-in validation.

## Overview
This agent provides a REST API endpoint that processes queries about Kubernetes cluster state and returns simplified answers. It does so by performing the following tasks:

1. Leverage the natural language processing (NLP) capabilities of GPT-4o-mini to understand the intent of user queries.
2. Extract the relevant information from a Kubernetes cluster using the Kubernetes API.

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
- Removed async support to simplify the code.
- Modern use of OpenAI API based on recent documentation.
- Switched to GPT-4o-mini model for faster, cost-effective query processing.
- Improved system prompt following prompt engineering best practices.

#### TODO
- Add a helper function (`get_kubernetes_info`) to retrieve information based on the classified query.
- Handle query processing and return appropriate responses (including error checking and handling).
- Complete server startup configuration in `main`.
