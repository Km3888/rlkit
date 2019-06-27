"""
Launcher for experiments with PEARL

"""
import os
import os.path as osp
import pathlib
import numpy as np
import click
import json
import copy
import pickle
import datetime
import torch

from rlkit.envs import ENVS
from rlkit.envs.wrappers import NormalizedBoxEnv
from rlkit.torch.sac.policies import TanhGaussianPolicy
from rlkit.torch.networks import FlattenMlp, MlpEncoder, RecurrentEncoder
from rlkit.torch.sac.sac import PEARLSoftActorCritic
from rlkit.torch.sac.agent import PEARLAgent
from rlkit.launchers.launcher_util import setup_logger
import rlkit.torch.pytorch_util as ptu
from configs.default import default_config
from rlkit.launchers.send_email import _send_email


def experiment(variant):
    # create multi-task environment and sample tasks
    if ("sawyer_reach_real" in variant['env_name']):  # We need a separate import because this can only be done when on a ROS computer
        from rlkit.envs.sawyer_reach_real import MultitaskSawyerReachEnv
        env = NormalizedBoxEnv(MultitaskSawyerReachEnv(**variant['env_params']))
    else:
        env = NormalizedBoxEnv(ENVS[variant['env_name']](**variant['env_params']))
    tasks = env.get_all_task_idx()
    obs_dim = int(np.prod(env.observation_space.shape))
    action_dim = int(np.prod(env.action_space.shape))

    # instantiate networks
    latent_dim = variant['latent_size']
    context_encoder = latent_dim * 2 if variant['algo_params']['use_information_bottleneck'] else latent_dim
    reward_dim = 1
    net_size = variant['net_size']
    recurrent = variant['algo_params']['recurrent']
    encoder_model = RecurrentEncoder if recurrent else MlpEncoder

    context_encoder = encoder_model(
        hidden_sizes=[200, 200, 200],
        input_size=obs_dim + action_dim + reward_dim,
        output_size=context_encoder,
    )
    qf1 = FlattenMlp(
        hidden_sizes=[net_size, net_size, net_size],
        input_size=obs_dim + action_dim + latent_dim,
        output_size=1,
    )
    qf2 = FlattenMlp(
        hidden_sizes=[net_size, net_size, net_size],
        input_size=obs_dim + action_dim + latent_dim,
        output_size=1,
    )
    vf = FlattenMlp(
        hidden_sizes=[net_size, net_size, net_size],
        input_size=obs_dim + latent_dim,
        output_size=1,
    )
    policy = TanhGaussianPolicy(
        hidden_sizes=[net_size, net_size, net_size],
        obs_dim=obs_dim + latent_dim,
        latent_dim=latent_dim,
        action_dim=action_dim,
    )
    agent = PEARLAgent(
        latent_dim,
        context_encoder,
        policy,
        **variant['algo_params']
    )

    # optionally load pre-trained weights
    checkpoint = None
    if variant['continue_training']:
        if variant['path_to_checkpoint'] is None:
            raise Exception('Must specify checkpoint to continue training from')
        # checkpoint contains model weights, optimizer settings
        checkpoint = torch.load(osp.join(variant['path_to_checkpoint'], 'checkpoint.pth.tar'))

        # load model weights
        print('loading saved model weights...')
        context_encoder.load_state_dict(checkpoint['context_encoder_weights'])
        qf1.load_state_dict(checkpoint['qf1_weights'])
        qf2.load_state_dict(checkpoint['qf2_weights'])
        vf.load_state_dict(checkpoint['vf_weights'])
        policy.load_state_dict(checkpoint['policy_weights'])

    # optional GPU mode, move nets to gpu
    ptu.set_gpu_mode(variant['util_params']['use_gpu'], variant['util_params']['gpu_id'])
    if ptu.gpu_enabled():
        for net in [context_encoder, qf1, qf2, vf, policy]:
            net.to(ptu.device)

    # instantiate algorithm, creates optimizers
    algorithm = PEARLSoftActorCritic(
        env=env,
        train_tasks=list(tasks[:variant['n_train_tasks']]),
        eval_tasks=list(tasks[-variant['n_eval_tasks']:]),
        nets=[agent, qf1, qf2, vf],
        latent_dim=latent_dim,
        **variant['algo_params']
    )

    # if continuing training, load saved optimizer settings and replay buffers
    if variant['continue_training']:
        # TODO hacky, instantiate target vf net in this script?
        algorithm.networks[-2].load_state_dict(checkpoint['target_vf_weights'])
        algorithm.networks[-2].to(ptu.device)

        # NOTE: must do this AFTER loading model weights and moving them to gpu
        # see this issue: https://github.com/pytorch/pytorch/issues/2830
        print('loading saved model optimizers...')
        algorithm.policy_optimizer.load_state_dict(checkpoint['policy_optimizer'])
        algorithm.qf1_optimizer.load_state_dict(checkpoint['qf1_optimizer'])
        algorithm.qf2_optimizer.load_state_dict(checkpoint['qf2_optimizer'])
        algorithm.vf_optimizer.load_state_dict(checkpoint['vf_optimizer'])
        algorithm.context_optimizer.load_state_dict(checkpoint['context_optimizer'])

        if ptu.gpu_enabled():
            algorithm.to_optimizers()

        # load the replay buffers
        try:
            print('loading saved replay buffers...')
            algorithm.replay_buffer = torch.load(osp.join(variant['path_to_checkpoint'], 'replay_buffer.pth.tar'))
            algorithm.enc_replay_buffer = torch.load(osp.join(variant['path_to_checkpoint'], 'enc_replay_buffer.pth.tar'))
            algorithm.skip_init_data_collection = True
        except:
            print('failed to load replay buffers')

    else:
        try:
            print('trying to load saved initial data...')
            #algorithm.replay_buffer = torch.load(osp.join(variant['path_to_checkpoint'], 'init_buffer.pth.tar'))
            # TODO delete when no longer using this old-style checkpoint
            with open(osp.join(variant['path_to_checkpoint'], 'init_buffer.pkl'), 'rb') as f:
                algorithm.replay_buffer = pickle.load(f)

            algorithm.enc_replay_buffer = copy.deepcopy(algorithm.replay_buffer)
            algorithm.skip_init_data_collection = True
            print('success!')
            print('sizes', [t._size for t in algorithm.replay_buffer.task_buffers.values()])
        except:
            print('tried and failed to load initial data buffer')

    # optional GPU mode
    ptu.set_gpu_mode(variant['util_params']['use_gpu'], variant['util_params']['gpu_id'])
    if ptu.gpu_enabled():
        algorithm.to()

    # debugging triggers a lot of printing and logs to a debug directory
    DEBUG = variant['util_params']['debug']
    os.environ['DEBUG'] = str(int(DEBUG))

    # create logging directory
    # TODO support Docker
    exp_id = 'debug' if DEBUG else None
    experiment_log_dir = setup_logger(variant['env_name'], variant=variant, exp_id=exp_id, base_log_dir=variant['util_params']['base_log_dir'])

    # optionally save eval trajectories as pkl files
    if variant['algo_params']['dump_eval_paths']:
        pickle_dir = experiment_log_dir + '/eval_trajectories'
        pathlib.Path(pickle_dir).mkdir(parents=True, exist_ok=True)

    # run the algorithm
    algorithm.train()

def deep_update_dict(fr, to):
    ''' update dict of dicts with new values '''
    # assume dicts have same keys
    for k, v in fr.items():
        if type(v) is dict:
            deep_update_dict(v, to[k])
        else:
            to[k] = v
    return to

@click.command()
@click.argument('config', default=None)
@click.option('--gpu', default=0)
@click.option('--docker', is_flag=True, default=False)
@click.option('--debug', is_flag=True, default=False)
def main(config, gpu, docker, debug):

    variant = default_config
    if config:
        with open(os.path.join(config)) as f:
            exp_params = json.load(f)
        variant = deep_update_dict(exp_params, variant)
    variant['util_params']['gpu_id'] = gpu

    start_time = datetime.datetime.now()
    try:
        experiment(variant)
    except:
        _send_email('exception raised', start_time)
    else:
        _send_email('experiment finished', start_time)

if __name__ == "__main__":
    main()

