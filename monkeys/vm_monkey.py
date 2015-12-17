from common import utils
import monkey
import random
import threading


class VMMonkey(monkey.Monkey):

    def __init__(self, vc, cf):
        monkey.Monkey.__init__(self, vc, cf, 'vm')

    def get_plan(self, regulars, actions, number):
        threads = []
        vm_list = self.vc.get_vms_by_regex(regulars)
        if len(vm_list) < number:
            number = len(vm_list)
        target_list = random.sample(vm_list, number)
        for vm in target_list:
            action = random.choice(actions)
            threads.append(self._get_thread(vm, action))
        return threads

    def _get_thread(self, vm, action):
        if action == 'migrate':
            host = vm.get_host()
            dss = host.get_datastores()
            size = vm.get_size()
            vm_ds = None
            random.shuffle(dss)
            for ds in dss:
                if ds.get_freespace() > size:
                    vm_ds = ds
                    break
            if vm_ds is None:
                vm_ds = vm.get_datastores[0]
            return threading.Thread(target=self.call_func,
                                    args=(vm, action, (host, vm_ds,)))
        func_dict = {'clone': (vm.name() + '_clone_' + utils.get_randstr(5),),
                     'snapshot': (vm.name() + '_snap_' + utils.get_randstr(5),),
                     'poweron': (),
                     'poweroff': (),
                     'reset': (),
                     'destroy': (),
                     'unregister': ()}
        return threading.Thread(target=self.call_func,
                                args=(vm, action, func_dict[action]))