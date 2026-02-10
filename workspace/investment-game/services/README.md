# Investment Game Services

This directory contains all the services required to perform an investment game experiment.

### Prerequisites

1.  **Docker Engine**: Ensure the Docker daemon is running before starting the services.
2.  **Docker Compose**: Docker Compose (v2+) is required to run all containers.
3.  **[sshpass](https://sshpass.com/)**: Required to push code to Pepper via SSH ([Homebrew Formulae](https://formulae.brew.sh/formula/sshpass))

### Deployment

Use the provided script to start all services:

```bash
export PEPPER_PASS="your_pepper_ssh_password"
export GEMINI_API_KEY="your_gemini_api_key"

chmod +x run.sh
./run.sh
```

This will:

- Start all services in the foreground (`docker compose up`)
- Create any required Docker volumes
- Ensure service dependencies are handled automatically

To stop all services and clean up everything, run:

```bash
chmod +x cleanup.sh
./cleanup.sh
```

> **NOTE:** To view Audio Forwarder logs, SSH into Pepper by running:

```bash
ssh nao@pepper.local
```
