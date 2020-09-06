# Reinforcement learning agents

## Setup
1. Install additional dependencies (`pip install -r requirements.txt`)
2. Start backend with the generate_destinations flag (e.g. `python main.py --domain=microworld --generate_destinations`)
3. (Optional) Start the frontend to see what the agents are saying
4. Run the training script from this directory: `python train.py`

## Arguments
- `--debug`: Whether to run rllib in debug mode, which runs workers on a single thread and lets you set breakpoints
- `--num_workers`: How many workers to use for training. Each worker connects to a different room, so it should not exceed the number of rooms running in the backend.
- `--backend_url` and `--backend_port`: Where the backend is running (defaults to localhost:5000)
