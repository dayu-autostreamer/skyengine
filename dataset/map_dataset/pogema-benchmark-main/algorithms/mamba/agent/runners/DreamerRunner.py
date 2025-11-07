import os
from datetime import datetime

import ray

import wandb
from mamba.agent.workers.DreamerWorker import DreamerWorker


class DreamerServer:
    def __init__(self, n_workers, env_config, controller_config, model):
        ray.init()

        self.workers = [
            DreamerWorker.remote(i, env_config, controller_config)
            for i in range(n_workers)
        ]
        self.tasks = [worker.run.remote(model) for worker in self.workers]
        self.non_remote = DreamerWorker.remote(0, env_config, controller_config)

    def append(self, idx, update):
        self.tasks.append(self.workers[idx].run.remote(update))

    def run(self):
        done_id, tasks = ray.wait(self.tasks)
        self.tasks = tasks
        recvs = ray.get(done_id)[0]
        return recvs


class DreamerRunner:

    def __init__(
        self,
        wandb_config,
        env_config,
        learner_config,
        controller_config,
        n_workers,
        save_dir,
        save_every,
        checkpoint_path,
        evaluate=False,
    ):
        self.n_workers = n_workers
        wandb_config["enable"] = not evaluate
        self.learner = learner_config.create_learner(wandb_config)
        if checkpoint_path is not None and os.path.exists(checkpoint_path):
            self.learner.load_params(checkpoint_path)
        else:
            print("No checkpoint has been loaded. Training from the init.")
        self.save_every = save_every
        try:
            os.makedirs(save_dir, exist_ok=True)
            self.save_dir = save_dir
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            os.makedirs(f"{save_dir}/{timestamp}", exist_ok=True)
            self.checkpoint_name = f"{save_dir}/{timestamp}/ckpt"
        except Exception as e:
            print(f"Couldn't create save dir due to {e}. Disabling save")
            self.save_dir = None
        if evaluate:
            anim_dir = f"animations/{save_dir}/{timestamp}"
            os.makedirs(anim_dir, exist_ok=True)
            env_config[0].RENDER = True
            env_config[0].SAVE_DIR = anim_dir
            self.rnn_states = None

        self.server = DreamerServer(
            n_workers, env_config, controller_config, self.learner.params()
        )

    def act(self, state):
        done_id = self.server.non_remote.act.remote(self.learner.params(), state)
        recvs = ray.get(done_id)[0]
        return recvs

    def reset_states(self):
        self.server.non_remote.reset.remote(self.learner.params())

    def eval(self, num_eval_episodes):

        wandb.define_metric("eval_steps")

        cur_episode = 0
        cur_steps = 0
        while cur_episode <= num_eval_episodes:
            _, info = self.server.run()

            cur_steps += info["steps_done"]
            cur_episode += 1
            wandb.log(
                {**{f"Eval/{k}": v for k, v in info.items()}, "eval_steps": cur_steps}
            )

            print(cur_episode, self.learner.total_samples, info)
            self.server.append(info["idx"], self.learner.params())

    def run(self, max_steps=10**10, max_episodes=10**10, num_eval_epiodes=1):
        cur_steps, cur_episode = 0, 0

        wandb.define_metric("steps")
        wandb.define_metric("reward", step_metric="steps")

        while True:
            rollout, info = self.server.run()

            self.learner.step(rollout)
            cur_steps += info["steps_done"]
            cur_episode += 1
            wandb.log({**info, "steps": cur_steps})

            print(cur_episode, self.learner.total_samples, info)

            if self.save_every > 0 and cur_episode % self.save_every == 0:
                if self.save_dir is not None:
                    self.learner.save_params(f"{self.checkpoint_name}_{cur_episode}.pt")

            if cur_episode >= max_episodes or cur_steps >= max_steps:
                break
            self.server.append(info["idx"], self.learner.params())
