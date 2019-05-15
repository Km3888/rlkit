README last updated on: 02/19/2018

# rlkit
Reinforcement learning framework and algorithms implemented in PyTorch.

Some implemented algorithms:
 - Temporal Difference Models (TDMs)
    - [example script](examples/tdm/cheetah.py)
    - [TDM paper](https://arxiv.org/abs/1802.09081)
    - [Details on implementation](rlkit/torch/tdm/TDMs.md)
 - Deep Deterministic Policy Gradient (DDPG)
    - [example script](examples/ddpg.py)
    - [DDPG paper](https://arxiv.org/pdf/1509.02971.pdf)
 - (Double) Deep Q-Network (DQN)
    - [example script](examples/dqn_and_double_dqn.py)
    - [DQN paper](https://arxiv.org/pdf/1509.06461.pdf)
    - [Double Q-learning paper](https://arxiv.org/pdf/1509.06461.pdf)
 - Soft Actor Critic (SAC)
    - [example script](examples/sac.py)
    - [SAC paper](https://arxiv.org/abs/1801.01290)
    - [TensorFlow implementation from author](https://github.com/haarnoja/sac)
 - Twin Dueling Deep Determinstic Policy Gradient (TD3)
    - [example script](examples/td3.py)
    - [TD3 paper](https://arxiv.org/abs/1802.09477)

To get started, checkout the example scripts, linked above.

## Installation
Install and use the included Ananconda environment
```
$ conda env create -f docker/rlkit/rlkit-env.yml
$ source activate rlkit
(rlkit) $ python examples/ddpg.py
```

There is also a GPU-version in `docker/rlkit-gpu`
```
$ conda env create -f docker/rlkit_gpu/rlkit-env.yml
$ source activate rlkit-gpu
(rlkit-gpu) $ python examples/ddpg.py
```

NOTE: these Anaconda environments use MuJoCo 1.5 and gym 0.10.5, unlike previous versions.

For an even more portable solution, try using the docker image provided in `docker/rlkit_gpu`.
The Anaconda env should be enough, but this docker image addresses some of the rendering issues that may arise when using MuJoCo 1.5 and GPUs.
To use the GPU docker image, you will need a GPU and [nvidia-docker installed](https://github.com/nvidia/nvidia-docker/wiki/Installation-(version-2.0)).
Note that you'll need to [get your own MuJoCo key](https://www.roboti.us/license.html) if you want to use MuJoCo.

## Real World Experiments
### Enabling the Controller
1. `cd ~/ros_ws`
2. `./lordi.sh` (or whatever robot you are going to use)
3. `roslaunch ~/ros_ws/src/sawyer_control/exp_nodes.launch` To start the controller
4. Open a new terminal:
5. `rosrun intera_interface enable_robot.py -e` To enable the robot
* To disable the robot, you can run `rosrun intera_interface enable_robot.py -d` 
* Note: sometimes the IK controller will fail and you will see an error message. The
robot controller is still running even after this so you do not need to restart it.

### Running the script
1. `cd ~/ros_ws`
2. `./lordi.sh` (or whatever robot you are going to use). You need to start a 
separate terminal for the script (in addition to the controller script)
3. `cd ~/Documents/sawyer_pearl`
4. `python3 sawyer_reach_PEARL.py`

### Other Stuff
To define the safety bounds of the Sawyer you can run:
1. `cd ~/ros_ws`
2. `./lordi.sh` (or whatever robot you are going to use). You need to start a 
separate terminal for the script (in addition to the controller script)
3. `cd ~/Documents/sawyer_pearl`
4. `python print_cartesian_positions.py`. The coordinates of the end-effector (as well as its orientation) will be displayed.
Make sure you are looking at the end-effector position and not its orientation.
The x-value is forward and back, the y-value is left and right, the z-value is up and down. 
5. Make the necessary edits to `~/ros_ws/src/sawyer_control/src/sawyer_control/configs/pearl_lordi_config.py`

If you want to define a torque safety box, you can look at `base_config` for an example.

## Visualizing a policy and seeing results
During training, the results will be saved to a file called under
```
LOCAL_LOG_DIR/<exp_prefix>/<foldername>
```
 - `LOCAL_LOG_DIR` is the directory set by `rlkit.launchers.config.LOCAL_LOG_DIR`. Default name is 'output'.
 - `<exp_prefix>` is given either to `setup_logger`.
 - `<foldername>` is auto-generated and based off of `exp_prefix`.
 - inside this folder, you should see a file called `params.pkl`. To visualize a policy, run

```
(rlkit) $ python scripts/sim_policy.py LOCAL_LOG_DIR/<exp_prefix>/<foldername>/params.pkl
```

If you have rllab installed, you can also visualize the results
using `rllab`'s viskit, described at
the bottom of [this page](http://rllab.readthedocs.io/en/latest/user/cluster.html)

tl;dr run

```bash
python rllab/viskit/frontend.py LOCAL_LOG_DIR/<exp_prefix>/
```

Alternatively, if you don't want to clone all of `rllab`, a repository containing only viskit can be found [here](https://github.com/vitchyr/viskit).
Then you can similarly visualize results with.
```bash
python viskit/viskit/frontend.py LOCAL_LOG_DIR/<exp_prefix>/
```

## Visualizing a TDM policy
To visualize a TDM policy, run
```
(rlkit) $ python scripts/sim_tdm_policy.py LOCAL_LOG_DIR/<exp_prefix>/<foldername>/params.pkl
```

## Algorithm-Specific Comments
### SAC
The SAC implementation provided here only uses Gaussian policy, rather than a Gaussian mixture model, as described in the original SAC paper.

## Credits
A lot of the coding infrastructure is based on [rllab](https://github.com/rll/rllab).
The serialization and logger code are basically a carbon copy of the rllab versions.

The Dockerfile is based on the [OpenAI mujoco-py Dockerfile](https://github.com/openai/mujoco-py/blob/master/Dockerfile).
