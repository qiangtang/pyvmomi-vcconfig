from common import utils


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
                number_str = self.cf.get(section, 'number')
                number = len(targets) if '' == number_str else int(number_str)
                plan.extend(self.get_plan(targets, actions, number))
        return plan

    def call_func(self, instance, name, args=(), kwargs=None):
        if kwargs is None:
            kwargs = {}
        return getattr(instance, name)(*args, **kwargs)

    def get_plan(self, regulars, actions, number):
        return []

    def restore(self):
        pass