
# MAMBA benchmark

## Installation

Via `Docker` to build the repo using the following script:
```Bash
cd docker/mamba; bash build.sh
```
### Training
To train, firstly you need to install `crafting`:
```Bash
pip install -U crafting
```

Secondly, you need to create / set up your `wandb` token:
```Bash
export WANDB_API_KEY=YOURAPIKEY
```

## Evaluation

Put a path to your checkpoint to the [config](./inference/inference_config.py):

```Python
    name = "MAMBA"
    num_envs: int = 1
    preprocessing: PreprocessorConfig = PreprocessorConfig()
    path_to_weights: str = "./mamba/benchmark/ckpt_oneshot_8agents.pt"  
    num_agents: int = 8
    training_config: Optional[Any] = None
    custom_path_to_save_gifs: Optional[str] = "./renders"
    use_follower_wrapper: Optional[bool] = True
    env_name: Optional[str] = "benchmark_follower_pogema_env_mazes_random"
    on_target = "nothing" #`nothing` for one-shot mapf, `restart` — for lifelong 
```

And lastly,
```Bash
crafting run.yaml
```
