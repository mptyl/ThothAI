# ThothAI Installation Overview

Welcome to the ThothAI installation documentation. ThothAI installation is flexible and designed to adapt to various needs, from local development to production on distributed clusters.

This guide will help you choose the installation mode that best suits your requirements.

## Installation Variations

There are three main "variations" or dimensions to consider for installation:

### 1. Installation Mode
This is the fundamental choice on how to obtain the software:

*   **Source Installation**: Ideal for developers who want to contribute to the code or need deep customizations. Allows compiling Docker images (Build) and Pushing to a custom registry. Requires cloning the GitHub repository.
    *   *See Manual 2: Source Installation*

*   **CLI Assisted Installation**: Ideal for end-users and system administrators. Uses the `thothai-cli` tool (installable via `uv` or `pip`) to automatically download and configure the environment without manually managing source code.
    *   *See Manuals 3 and 4*

### 2. Infrastructure Topology
ThothAI supports two Docker architectures:

*   **Single Node (Docker Compose)**: The entire application runs on a single machine (laptop, server, or VM). This is the simplest mode and recommended for testing, development, and small installations.
    *   *See Manual 3: CLI Installation on Docker Compose*

*   **Cluster (Docker Swarm)**: The application is distributed across multiple nodes for high availability and scalability. This is the recommended mode for production and enterprise environments.
    *   *See Manual 4: CLI Installation on Docker Swarm*

### 3. Installation Location
Regardless of the mode and topology, you can install ThothAI:

*   **Locally**: On your current computer (e.g., a developer installing on their laptop) or by directly accessing the destination server.
*   **Remotely**: From your local computer to a remote server (e.g., VPS or corporate server) via SSH connection automatically managed by the CLI.

### Security Note: SSL/TLS

ThothAI exposes services over HTTP. For production deployments, it is recommended to configure a reverse proxy with SSL termination (nginx, Apache, Traefik, HAProxy) according to your organization's security policies.

## Manuals Index

To proceed, select the appropriate manual:

1.  **[1_INSTALLATION_OVERVIEW.md](1_INSTALLATION_OVERVIEW.md)**: This document.
2.  **[2_SOURCE_INSTALLATION.md](2_SOURCE_INSTALLATION.md)**: Guide for source installation (git clone, custom build, `install.sh`/`install.ps1` scripts).
3.  **[3_CLI_COMPOSE_INSTALLATION.md](3_CLI_COMPOSE_INSTALLATION.md)**: Guide for CLI installation on a single node (Compose), local or remote. Includes options for Docker Hub or private Registry.
4.  **[4_CLI_SWARM_INSTALLATION.md](4_CLI_SWARM_INSTALLATION.md)**: Guide for CLI installation on a Swarm cluster, local or remote. Includes options for Docker Hub or private Registry.
5.  **[5_CLI_MANAGEMENT.md](5_CLI_MANAGEMENT.md)**: Guide for post-installation management (automatic updates, cleanup, status check) via CLI.
