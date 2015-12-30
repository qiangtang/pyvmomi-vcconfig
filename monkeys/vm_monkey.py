from common import utils
import monkey
import random
import threading


class VMMonkey(monkey.Monkey):

    def __init__(self, vc, cf):
        monkey.Monkey.__init__(self, vc, cf, 'vm')

    def get_plan(self, policy, regulars, actions, number):
        vm_list = self.vc.get_vms_by_regex(regulars)
        if len(vm_list) < number:
            number = len(vm_list)
        threads = self.policy_threads(policy, vm_list, actions, number)
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
        randstr = utils.get_randstr(5)
        func_dict = {'clone': (vm.name() + '_clone_' + randstr,),
                     'snapshot': (vm.name() + '_snap_' + randstr,),
                     'poweron': (),
                     'poweroff': (),
                     'reset': (),
                     'destroy': (),
                     'unregister': ()}
        if action == 'snapshot' or action == 'clone':
            if action not in self.restore_list.keys():
                self.restore_list[action] = []
            if action == 'snapshot' or action == 'poweron' or action == 'poweroff':
                self.restore_list[action].append(vm)
            elif action == 'clone':
                self.restore_list[action].append(vm.name() + '_clone_' + randstr)
        return threading.Thread(target=self.call_func,
                                args=(vm, action, func_dict[action]))

    def restore(self):
        thread_list = self.get_restore_list()
        for thread in thread_list:
            thread.start()
        for thread in thread_list:
            thread.join()
        self.restore_list.clear()

    def get_restore_list(self):
        thread_list = []
        restore_dist = {
            'clone': 'destroy',
            'poweron': 'poweroff',
            'poweroff': 'poweron',
            'snapshot': 'remove_snapshots'
        }
        for action in self.restore_list.keys():
            if action == 'clone':
                vms = [self.vc.get_vm_by_name(vm_name)
                       for vm_name in self.restore_list[action]]
            else:
                vms = self.restore_list[action]
            threads = [threading.Thread(target=self.call_func,
                                        args=(vm, restore_dist[action], ()))
                       for vm in vms]
            thread_list.extend(threads)
        return thread_list