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
cp controller/games.csv.example controller/games.csv
# edit controller/games.csv with real participant schedule

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

Piper values:

- `LENGTH_SCALE` (defaults to `0.72`) - tweak this to make Pepper speak faster or slower
- `NOISE_SCALE` (defualts to `0.9`)
- `NOISE_W_SCALE` (defaults to `0.8`)

Experiment confguration:

- `GAME_ROUNDS` (rounds per game, default `3`)

Experiment scheduling now uses `controller/games.csv` (see `controller/games.csv.example`).

- The tablet setup screen requires a participant id.
- Participant id must exist in `games.csv`.
- Game count and order are inferred from participant rows in `games.csv`.
- If a conversation file already exists for the participant, organizer override is required.
- Supported `condition` values in `games.csv`:
  - `LLM`: full LLM response generation
  - `ALG`: keyword matching from fixed response pools
  - `SEL-LLM`: LLM-based selection from fixed pools; intro says "LLM-controlled"
  - `SEL-ALG`: LLM-based selection from fixed pools; intro says "Algorithmically controlled"

This will:

- Start all services in the foreground (`docker compose up`)
- Create any required Docker volumes
- Ensure service dependencies are handled automatically

> [!TIP]
> You may want to assign a static IP lease for your computer

To stop all services and clean up everything, run:

```bash
chmod +x cleanup.sh
./cleanup.sh
```

> [!TIP]
> To view Robot Handler logs, SSH into Pepper by running:

```bash
ssh nao@pepper.local
cat robot_handler.log
```
