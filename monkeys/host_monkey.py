from common import utils
from common import operations
import monkey
import random
import threading


class HostMonkey(monkey.Monkey):

    def __init__(self, vc, cf):
        monkey.Monkey.__init__(self, vc, cf, 'host')
        self.restore_list = {}

    def get_plan(self, host_names, actions, number):
        threads = []
        hosts = []
        for item in host_names:
            hosts.extend(operations.get_host_list(item))
        all_hosts = self.vc.get_hosts()
        host_list = [host for host in all_hosts if host.name() in hosts]
        if len(host_list) < number:
            number = len(host_list)
        target_list = random.sample(host_list, number)
        for host in target_list:
            action = random.choice(actions)
            threads.append(self._get_thread(host, action))
        return threads

    def _get_thread(self, host, action):
        func_dict = {'maintenance': (),
                     'reboot': (),
                     'disconnect': ()}
        if action != 'reboot':
            if action not in self.restore_list.keys():
                self.restore_list[action] = []
            self.restore_list[action].append(host)
        return threading.Thread(target=self.call_func,
                                args=(host, action, func_dict[action]))

    def restore(self):
        thread_list = []
        for action in self.restore_list.keys():
            if action == 'maintenance':
                for host in self.restore_list[action]:
                    thread_list.append(
                        threading.Thread(target=self.call_func,
                                         args=(host, action, ('exit',))))
                continue
            if action == 'disconnect':
                for host in self.restore_list[action]:
                    thread_list.append(
                        threading.Thread(target=self.call_func,
                                         args=(host, 'reconnect', ())))
        for thread in thread_list:
            thread.start()
        for thread in thread_list:
            thread.join()
        self.restore_list.clear()
