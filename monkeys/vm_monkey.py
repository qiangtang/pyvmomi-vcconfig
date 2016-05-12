from common import utils
import monkey
import random
import threadpool


class VMMonkey(monkey.Monkey):

    def __init__(self, vc, cf):
        monkey.Monkey.__init__(self, vc, cf, 'vm')
        self.init_resource()

    def init_resource(self):
        sections = self.cf.sections()
        for section in sections:
            if section.startswith(self.cf_item):
                regulars = utils.get_items(self.cf.get(section, 'targets'))
                vm_list = self.vc.get_vms_by_regex(regulars)
                self.item_dict[section] = vm_list

    def _get_request(self, vm, action):
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
            return threadpool.WorkRequest(self.call_func,
                                          args=(vm, action, (host, vm_ds,)))
        randstr = utils.get_randstr(3)
        func_dict = {'clone': (vm.name() + '_cln_' + randstr,),
                     'snapshot': (vm.name() + '_snp_' + randstr,),
                     'poweron': (),
                     'poweroff': (),
                     'reset': (),
                     'destroy': (),
                     'unregister': ()}
        if action not in self.restore_list.keys():
            self.restore_list[action] = []
        if action == 'snapshot' or action == 'poweron' or action == 'poweroff':
            self.restore_list[action].append(vm)
        elif action == 'clone':
            self.restore_list[action].append(vm.name() + '_cln_' + randstr)
        return threadpool.WorkRequest(self.call_func,
                                      args=(vm, action, func_dict[action]))

    def get_restore_list(self):
        request_list = []
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
            requests = [threadpool.WorkRequest(self.call_func,
                                               args=(vm, restore_dist[action], ()))
                        for vm in vms]
            request_list.extend(requests)
        return request_list