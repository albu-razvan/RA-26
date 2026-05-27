# Amanuens in Research @ Chalmers '26

> [!NOTE]
> For a list of relevant changes, visit **[CHANGES.md](./CHANGES.md)**

> [!IMPORTANT]
> This repository has some pretty *big* files that require [Git Large File Storage](https://docs.github.com/en/repositories/working-with-files/managing-large-files/installing-git-large-file-storage) to be set up.Some of the scripts may fail otherwise.

## Getting Started

Pepper requires **Python 2.7** and **x86 dependencies** for its SDK. Because I hate setting up Rosetta on my M1 Mac, here's a **Docker** alternative ¯\\\_(ツ)\_/¯

### Prerequisites

1.  **Docker Desktop**: Ensure it is installed and running.
2.  **XQuartz (macOS only)**: Required to run GUI applications like Choregraphe.
    - Install via `brew install --cask xquartz`.
    - In XQuartz settings (**Settings > Security**), check **"Allow connections from network clients"**.
    - **Restart the computer** after configuration.

### Environment

A `run.armaapl` script automates the environment setup for Apple Silicon. To start the environment:

```bash
chmod +x run.armaapl
./run.armaapl
```

> [!IMPORTANT]
> `./workspace` folder will be mounted to the container. Any change made to `/workspace` in the Docker container will be reflected on the host.

To launch the GUI tools, execute the binaries `choregraphe-bin` or `robot_settings`.
