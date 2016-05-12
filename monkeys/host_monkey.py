from common import operations
from common import utils
import monkey
import threadpool


class HostMonkey(monkey.Monkey):

    def __init__(self, vc, cf):
        monkey.Monkey.__init__(self, vc, cf, 'host')
        self.init_resource()

    def init_resource(self):
        sections = self.cf.sections()
        for section in sections:
            if section.startswith(self.cf_item):
                hosts = []
                host_names = utils.get_items(self.cf.get(section, 'targets'))
                for item in host_names:
                    hosts.extend(operations.get_host_list(item))
                all_hosts = self.vc.get_hosts()
                host_list = [host for host in all_hosts if host.name() in hosts]
                self.item_dict[section] = host_list

    def _get_request(self, host, action):
        func_dict = {'maintenance': (),
                     'reboot': (),
                     'disconnect': ()}
        if action != 'reboot':
            if action not in self.restore_list.keys():
                self.restore_list[action] = []
            self.restore_list[action].append(host)
        return threadpool.WorkRequest(self.call_func,
                                      args=(host, action, func_dict[action]))

    def get_restore_list(self):
        request_list = []
        for action in self.restore_list.keys():
            if action == 'maintenance':
                for host in self.restore_list[action]:
                    request_list.append(
                        threadpool.WorkRequest(self.call_func,
                                               args=(host, action, ('exit',))))
                continue
            if action == 'disconnect':
                for host in self.restore_list[action]:
                    request_list.append(
                        threadpool.WorkRequest(self.call_func,
                                               args=(host, 'reconnect', ())))
        return request_list