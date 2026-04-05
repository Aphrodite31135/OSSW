# HW2 Assignment Summary

## One-Line Summary

This homework is about building a simple AI application and proving an end-to-end MLOps flow:

`code change -> GitHub push -> Docker image build -> Docker Hub push -> self-hosted deployment -> automatic service update`

## Core Goal

The assignment is not just "make an AI app."

It is meant to prove that you can:

- build an AI application
- containerize it with Docker
- automate image build with GitHub Actions
- push the image to Docker Hub
- deploy it automatically on a local machine using a self-hosted runner
- update the service automatically after changing the code

## Main Assignment Stages

### 1. Build a Simple AI API Server

Create a small AI application in a Linux-based development environment using AI-assisted development.

Example ideas:

- sentiment analysis
- face recognition
- age prediction

At minimum, the project should include:

- working AI app source code
- `requirements.txt`
- a clear project structure

### 2. Build the CI Pipeline

Create a GitHub repository and connect it to Docker Hub.

Prepare these GitHub Actions secrets:

- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`

Create:

- `Dockerfile`
- `.github/workflows/ci.yml`

The expected CI behavior:

- when code is pushed to GitHub
- Docker image is built automatically
- Docker image is pushed to Docker Hub automatically

### 3. Build the CD Pipeline

Use a self-hosted runner so that the local machine acts like a deployment server.

General deployment flow:

- register the local machine as a GitHub Actions self-hosted runner
- keep the runner active
- when a new image is available, stop the old container
- pull the latest image
- run the new container automatically

### 4. Verify Update and Redeployment

After the first version works, modify the model or features and push again.

Then verify:

- image is rebuilt
- deployment runs again
- the local service updates automatically

This is the part that demonstrates actual MLOps practice.

## Recommended Project Strategy

The safest strategy is:

1. start with a very simple FastAPI app
2. finish CI/CD first
3. then add one meaningful feature
4. show that automatic redeployment works after the update

## Planned Project Scope For This Submission

### First Release

`image -> 3D asset`

The user uploads an image and the app generates a 3D asset result.
This version includes a Web UI.

### Second Release

`text -> image -> 3D asset`

Add a text-to-image step so that the user can start from a text prompt and still end up with a 3D asset.
This version also includes a user-facing UI update.

## Blue-Green Deployment Note

For redeployment, the project will also include a Blue-Green deployment story.

The intended logic is:

- if Blue is serving traffic, start the new version on Green
- confirm the new version works
- switch service to the new version
- remove the old version

For the homework, a simplified Blue-Green deployment flow is acceptable as long as the deployment intent and update behavior are clearly demonstrated.

## Submission Checklist

The final submission should show evidence of:

- GitHub repository
- AI app source code
- `Dockerfile`
- GitHub Actions workflow files
- successful Docker Hub push
- self-hosted runner registration and execution
- successful automatic deployment
- final API or Web UI screen
- successful redeployment after a feature update

## Final Deliverables

The submission should include:

- screenshots
- a one-page report
- final compressed file named in this format:
  `StudentID_Name_HW2.zip`

## Practical Interpretation

In short, the assignment asks you to prove:

- you can build an AI app
- you can package it with Docker
- you can automate CI with GitHub Actions
- you can prepare and execute CD with Docker Hub and a self-hosted runner
- you can update the service automatically after changing the code
