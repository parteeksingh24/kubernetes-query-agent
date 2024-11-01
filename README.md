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
- Refactored code to a more modular approach (e.g., utilities functions, client initialization).
- Extended query classification from 4 types to 14 types, covering a wider range of potential queries.
- Restructured query handling logic to use class-based approach.

#### TODO
- Expand error handling (e.g., missing parameters, Kubernetes API failures).
- Add setup instructions and usage documentation.
