from common import utils
import random


class Monkey(object):

    def __init__(self, vc, cf, item_type):
        self.cf_item = utils.SCH_PREFIX + item_type.lower()
        self.vc = vc
        self.cf = cf
        self.restore_list = {}

    def planner(self):
        plan = []
        sections = self.cf.sections()
        for section in sections:
            if section.startswith(self.cf_item):
                targets = utils.get_items(self.cf.get(section, 'targets'))
                actions = utils.get_items(self.cf.get(section, 'actions'))
                if targets is None or actions is None:
                    continue
                number_str = self.cf.get(section, 'target_number')
                number = len(targets) if '' == number_str else int(number_str)
                policy = self.cf.get(section, 'policy').strip().lower()
                plan.extend(self.get_plan(policy, targets, actions, number))
        return plan

    def call_func(self, instance, name, args=(), kwargs=None):
        if kwargs is None:
            kwargs = {}
        return getattr(instance, name)(*args, **kwargs)

    def get_plan(self, policy, regulars, actions, number):
        return []

    def policy_threads(self, policy, target_list, actions, number):
        threads = []
        len_targets = len(target_list)
        if number > len_targets:
            number = len_targets
        targets = random.sample(target_list, number)
        random.shuffle(actions)
        if policy == 'action_base':
            len_act = len(actions)
            for i in range(len(targets)):
                threads.append(self._get_thread(targets[i],
                                                actions[i % len_act]))
        else:
            for target in targets:
                action = random.choice(actions)
                threads.append(self._get_thread(target, action))
        return threads

    def _get_thread(self, target, action):
        return None

    def restore(self):
        pass