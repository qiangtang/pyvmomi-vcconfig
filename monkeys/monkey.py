from common import utils


class Monkey(object):

    def __init__(self, vc, cf, item_type):
        self.cf_item = utils.SCH_PREFIX + item_type.lower()
        self.vc = vc
        self.cf = cf

    def planner(self):
        plan = []
        sections = self.cf.sections()
        for section in sections:
            if section.startswith(self.cf_item):
                regulars = utils.get_items(self.cf.get(section, 'regulars'))
                actions = utils.get_items(self.cf.get(section, 'actions'))
                number = int(self.cf.get(section, 'number'))
                plan.extend(self.get_plan(regulars, actions, number))
        return plan

    def call_func(self, instance, name, args=(), kwargs=None):
        if kwargs is None:
            kwargs = {}
        return getattr(instance, name)(*args, **kwargs)

    def get_plan(self, regulars, actions, number):
        return []