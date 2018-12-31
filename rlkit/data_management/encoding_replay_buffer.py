import numpy as np

from rlkit.data_management.env_replay_buffer import MultiTaskReplayBuffer
# from rlkit.data_management.onpolicy_replay_buffer import OnpolicyReplayBuffer
from rlkit.data_management.simple_replay_buffer import SimpleReplayBuffer


from gym.spaces import Box, Discrete, Tuple


# TODO: Delete this class?

# (AZ): Do we see any reason why we need different logic for the encoding replay buffer?
class EncodingReplayBuffer(MultiTaskReplayBuffer):
    def __init__(
            self,
            max_replay_buffer_size,
            env,
            tasks,
    ):
        """
        :param max_replay_buffer_size:
        :param env:
        :param tasks: for multi-task setting
        """
        self.env = env
        self._ob_space = env.observation_space
        self._action_space = env.action_space
        self.task_buffers = [SimpleReplayBuffer(
            max_replay_buffer_size=max_replay_buffer_size,
            observation_dim=get_dim(self._ob_space),
            action_dim=get_dim(self._action_space),
        ) for t in tasks]


    def add_sample(self, task, observation, action, reward, terminal,
            next_observation, **kwargs):


        if isinstance(self._action_space, Discrete):
            action = np.eye(self._action_space.n)[action]
        self.task_buffers[task].add_sample(
                observation, action, reward, terminal,
                next_observation, **kwargs)
        # self.task_buffers[task].add_sample(
        #         observation, action, reward, terminal,
        #         next_observation, epoch, **kwargs)


    def random_batch(self, task, batch_size):
        return self.task_buffers[task].random_batch(batch_size)

def get_dim(space):
    if isinstance(space, Box):
        return space.low.size
    elif isinstance(space, Discrete):
        return space.n
    elif isinstance(space, Tuple):
        return sum(get_dim(subspace) for subspace in space.spaces)
    elif hasattr(space, 'flat_dim'):
        return space.flat_dim
    else:
        raise TypeError("Unknown space: {}".format(space))
