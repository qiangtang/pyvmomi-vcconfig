from common import utils
import random
import threadpool


class Monkey(object):

    def __init__(self, vc, cf, item_type):
        self.cf_item = utils.SCH_PREFIX + item_type.lower()
        self.vc = vc
        self.cf = cf
        self.restore_list = {}
        self.item_type = item_type
        self.item_dict = {}

    def planner(self):
        plan = []
        sections = self.cf.sections()
        for section in sections:
            if section.startswith(self.cf_item):
                actions = utils.get_items(self.cf.get(section, 'actions'))
                if actions is None:
                    continue
                number_str = self.cf.get(section, 'target_number')
                number = len(self.item_dict) if '' == number_str else int(number_str)
                policy = self.cf.get(section, 'policy').strip().lower()
                plan.extend(self.get_plan(policy, section, actions, number))
        return plan

    def call_func(self, instance, name, args=(), kwargs=None):
        if kwargs is None:
            kwargs = {}
        return getattr(instance, name)(*args, **kwargs)

    def get_plan(self, policy, section, actions, number):
        if section not in self.item_dict.keys():
            return []
        item_list = self.item_dict[section]
        item_num = len(item_list)
        if 0 == item_num:
            return []
        if item_num < number:
            number = item_num
        requests = self.policy_requests(policy, item_list, actions, number)
        return requests

    def policy_requests(self, policy, target_list, actions, number):
        len_targets = len(target_list)
        if number > len_targets:
            number = len_targets
        targets = random.sample(target_list, number)
        random.shuffle(actions)
        if policy == 'action_base':
            len_act = len(actions)
            return [self._get_request(targets[i], actions[i % len_act])
                    for i in range(len(targets))]
        else:
            return [self._get_request(target, random.choice(actions))
                    for target in targets]

    def _get_request(self, target, action):
        return None

    def restore(self, poolsize=10):
        pool = threadpool.ThreadPool(poolsize)
        if len(self.get_restore_list()) == 0:
            return
        print 'Starting {} action restore...'.format(self.item_type)
        for req in self.get_restore_list():
            pool.putRequest(req)
        pool.wait()
        self.restore_list.clear()

    def get_restore_list(self):
        return []