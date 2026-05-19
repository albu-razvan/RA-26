# Investment Game Services

This directory contains all the services required to perform an investment game experiment.

### Prerequisites

1.  **Docker Engine**: Ensure the Docker daemon is running before starting the services.
2.  **Docker Compose**: Docker Compose (v2+) is required to run all containers.
3.  **[sshpass](https://sshpass.com/)**: Required to push code to Pepper via SSH ([Homebrew Formulae](https://formulae.brew.sh/formula/sshpass))

### Deployment

Use the provided script to start all services:

```bash
cp .env.example .env
# edit .env and set your real values

chmod +x run.sh
./run.sh
```

Required `.env` values are:

- `PEPPER_PASS`
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_DEPLOYMENT` (for example `gpt-5.4-nano`)
- `HF_TOKEN`
- `ROBOT_IP`
- `COMPUTER_IP`

Optional `.env` values:

- `AZURE_OPENAI_API_VERSION` (defaults to `2025-03-01-preview` in code)
- `STT_MODEL` (defaults to `base.en`)
- `SILENCE_LIMIT_FRAMES` (defaults to `55`)

This will:

- Start all services in the foreground (`docker compose up`)
- Create any required Docker volumes
- Ensure service dependencies are handled automatically

> **NOTE:** You may want to assign a static IP lease for your computer

To stop all services and clean up everything, run:

```bash
chmod +x cleanup.sh
./cleanup.sh
```

> **NOTE:** To view Audio Forwarder logs, SSH into Pepper by running:

```bash
ssh nao@pepper.local
cat audio_handler.log
```
