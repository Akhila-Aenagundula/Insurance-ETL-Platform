# Insurance ETL Platform – Microservices Development and Deployment

## Project Overview
A microservices-based Insurance ETL Platform developed using Python and FastAPI to ingest, process, validate, and transform insurance policy data.

## Technologies Used
- Python
- FastAPI
- Pandas
- HTTPX
- Docker
- Docker Compose
- Kubernetes
- Minikube

## Architecture
The application consists of two independent microservices:

1. **Ingestion Service:** Accepts insurance policy CSV files and initiates processing.
2. **Processing Service:** Validates and processes records, producing curated and rejected datasets along with quality and audit reports.

The services communicate through REST APIs.

## Deployment
- Docker and Docker Compose for containerization.
- Kubernetes for orchestration.
- Minikube for local Kubernetes deployment.

## Execution
The application exposes API endpoints through FastAPI Swagger UI for file upload and testing.

## Project Status
Implemented and tested locally using Docker and Minikube.
