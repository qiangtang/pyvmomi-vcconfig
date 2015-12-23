from common import operations
import monkey
import threading


class HostMonkey(monkey.Monkey):

    def __init__(self, vc, cf):
        monkey.Monkey.__init__(self, vc, cf, 'host')

    def get_plan(self, policy, host_names, actions, number):
        hosts = []
        for item in host_names:
            hosts.extend(operations.get_host_list(item))
        all_hosts = self.vc.get_hosts()
        host_list = [host for host in all_hosts if host.name() in hosts]
        if len(host_list) < number:
            number = len(host_list)
        threads = self.policy_threads(policy, host_list, actions, number)
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
        thread_list = self.get_restore_list()
        for thread in thread_list:
            thread.start()
        for thread in thread_list:
            thread.join()
        self.restore_list.clear()

    def get_restore_list(self):
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
        return thread_list