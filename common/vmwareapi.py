"""Wrapper library for pyVmomi"""

import logging
import re
import pyVmomi
from pyVmomi import vim
import task


LOG = logging.getLogger(__name__)


def connect(host, user, password):
    stub = pyVmomi.SoapStubAdapter(
        host=host,
        port=443,
        version='vim.version.version6',
        path='/sdk',
        certKeyFile=None,
        certFile=None)

    si = vim.ServiceInstance("ServiceInstance", stub)
    content = si.RetrieveContent()
    content.sessionManager.Login(user, password, None)
    return si


def disconnect(si):
    content = si.RetrieveContent()
    content.sessionManager.Logout()


class ManagedObject(object):

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.disconnect()

    def disconnect(self):
        if self.si is not None:
            disconnect(self.si)
            self.si = None

    def get_root_folder(self, si):
        return si.RetrieveContent().rootFolder

    def get_obj(self, si, vimtype, name):
        """
        Get the vsphere object associated with a given text name
        """
        obj = None
        container = si.RetrieveContent().viewManager.\
            CreateContainerView(si.RetrieveContent().rootFolder, vimtype, True)
        for c in container.view:
            if c.name == name:
                obj = c
                break
        return obj


class VirtualCenter(ManagedObject):

    def __init__(self, host, user, pwd):
        self.host = host
        self.user = user
        self.pwd = pwd
        self.si = None

    def requires_connection(func):
        """Decorator that makes sure that we have active connection to virtual

        center
        @param func: method that is decorated
        @return: return decorator
        """

        def connect_me(self, *args, **kargs):
            if self.si is None:
                self.si = connect(self.host, self.user, self.pwd)
            return func(self, *args, **kargs)
        return connect_me

    @requires_connection
    def assign_role(self, user, role_name):
        authmgr = self.si.RetrieveContent().authorizationManager
        roles = authmgr.roleList
        role_id = 0
        for role in roles:
            if role.name == role_name:
                role_id = role.roleId
                break
            if role is roles[-1]:
                print("Failed to get target role.")
                return None
        permission = vim.AuthorizationManager.Permission()
        permission.principal = user
        permission.group = False
        permission.propagate = True
        permission.roleId = role_id
        authmgr.SetEntityPermissions(self.get_root_folder(self.si),
                                     [permission])

    @requires_connection
    def create_datacenter(self, name):
        """Creates a datacenter in the root folder.

        @param name: name of the datacenter
        @return returns Datacenter instance
        """
        rootFolder = self.get_root_folder(self.si)
        dc = rootFolder.CreateDatacenter(name)
        return Datacenter(self.si, dc)

    @requires_connection
    def get_datacenter_by_name(self, name):
        """Returns a reference to datacenter in the root folder.

        @param name: name of the datacenter
        @return returns Datacenter instance
        """
        vmgr = self.si.RetrieveContent().viewManager
        invtvw = vmgr.CreateContainerView(
            container=self.get_root_folder(self.si),
            type=[vim.Datacenter],
            recursive=True)
        for dc in invtvw.view:
            if dc.name == name:
                return Datacenter(self.si, dc)
        return None

    @requires_connection
    def get_vm_by_name(self, name, folder_name=None):
        """Returns a reference to vm by its name.

        @param name: name of the vm
        @return returns VirtualMachine instance
        """
        vmgr = self.si.RetrieveContent().viewManager
        invtvw = vmgr.CreateContainerView(
            container=self.get_root_folder(self.si),
            type=[vim.VirtualMachine],
            recursive=True)
        for vm in invtvw.view:
            if vm.name == name:
                if folder_name and vm.parent.name != folder_name:
                    continue
                return VM(self.si, vm)
        return None

    @requires_connection
    def get_datastore_by_name(self, name):
        vmgr = self.si.RetrieveContent().viewManager
        invtvw = vmgr.CreateContainerView(
            container=self.get_root_folder(self.si),
            type=[vim.Datastore],
            recursive=True)
        for ds in invtvw.view:
            if ds.name == name:
                return DataStore(self.si, ds)
        return None

    @requires_connection
    def get_host_by_name(self, name):
        vmgr = self.si.RetrieveContent().viewManager
        invtvw = vmgr.CreateContainerView(
            container=self.get_root_folder(self.si),
            type=[vim.HostSystem],
            recursive=True)
        for host in invtvw.view:
            if host.name == name:
                return Host(self.si, host)
        return None

    @requires_connection
    def get_log_bundle(self):
        def get_all_host_systems():
            vmgr = self.si.RetrieveContent().viewManager
            invtvw = vmgr.CreateContainerView(
                container=self.get_root_folder(self.si),
                type=[vim.HostSystem],
                recursive=True)
            return [h for h in invtvw.view]

        content = self.si.RetrieveContent()
        dmgr = content.diagnosticManager
        generate_task = dmgr.GenerateLogBundles_Task(
            includeDefault=True,
            host=get_all_host_systems())
        task.WaitForTask(generate_task, self.si)
        bundles = [b.url.replace("*", self.host)
                   for b in generate_task.info.result]
        return bundles

    @requires_connection
    def get_vapp_by_name(self, name):
        vmgr = self.si.RetrieveContent().viewManager
        invtvw = vmgr.CreateContainerView(
            container=self.get_root_folder(self.si),
            type=[vim.VirtualApp],
            recursive=True)
        for vapp in invtvw.view:
            if name in vapp.name:
                return Vapp(self.si, vapp)
        return None

    @requires_connection
    def get_datacenters(self):
        vmgr = self.si.RetrieveContent().viewManager
        invtvw = vmgr.CreateContainerView(
            container=self.get_root_folder(self.si),
            type=[vim.Datacenter],
            recursive=True)
        return [Datacenter(self.si, dc) for dc in invtvw.view]

    @requires_connection
    def get_hosts(self):
        vmgr = self.si.RetrieveContent().viewManager
        invtvw = vmgr.CreateContainerView(
            container=self.get_root_folder(self.si),
            type=[vim.HostSystem],
            recursive=True)
        return [Host(self.si, host) for host in invtvw.view]

    @requires_connection
    def get_vms_by_regex(self, regex_list):
        all_vms = []
        vmgr = self.si.RetrieveContent().viewManager
        invtvw = vmgr.CreateContainerView(
            container=self.get_root_folder(self.si),
            type=[vim.VirtualMachine],
            recursive=True)
        for regex in regex_list:
            for vm in invtvw.view:
                if re.match(regex, vm.name):
                    all_vms.append(VM(self.si, vm))
        return all_vms

    @requires_connection
    def get_nets_by_regex(self, regex_list):
        all_nets = []
        vmgr = self.si.RetrieveContent().viewManager
        invtvw = vmgr.CreateContainerView(
            container=self.get_root_folder(self.si),
            type=[vim.Network],
            recursive=True)
        for regex in regex_list:
            for net in invtvw.view:
                if re.match(regex, net.name):
                    all_nets.append(Network(self.si, net))
        return all_nets

    @requires_connection
    def get_folders_by_regex(self, regex_list):
        all_folders = []
        vmgr = self.si.RetrieveContent().viewManager
        invtvw = vmgr.CreateContainerView(
            container=self.get_root_folder(self.si),
            type=[vim.Folder],
            recursive=True)
        for regex in regex_list:
            for folder in invtvw.view:
                if re.match(regex, folder.name):
                    all_folders.append(Folder(self.si, folder))
        return all_folders

    @requires_connection
    def get_datastores(self, dc_name=None, ds_type=None):
        if dc_name:
            ds_list = self.get_datacenter_by_name(dc_name).dc.datastore
        else:
            vmgr = self.si.RetrieveContent().viewManager
            invtvw = vmgr.CreateContainerView(
                container=self.get_root_folder(self.si),
                type=[vim.Datastore],
                recursive=True)
            ds_list = [ds for ds in invtvw.view]

        if ds_type:
            from utils import DS_TYPE
            ds_type = ds_type.upper()
            if ds_type in DS_TYPE:
                return [DataStore(self.si, ds) for ds in ds_list
                        if ds.summary.type == ds_type]
            else:
                print "Invalid storage type: " + ds_type
                return None
        else:
            return [DataStore(self.si, ds) for ds in ds_list]


class Datacenter(ManagedObject):

    def __init__(self, si, dc):
        if not isinstance(dc, vim.Datacenter):
            raise TypeError("Not a vim.Datacenter object")
        self.dc = dc
        self.si = si

    def name(self):
        return self.dc.name

    def create_cluster(self, name, config=vim.cluster.ConfigSpecEx()):
        """Creates cluster.

        @param name: name of the cluster
        @param config: vim.cluster.ConfigSpecEx
        """

        hostFolder = self.dc.hostFolder
        c = hostFolder.CreateClusterEx(name, config)
        return Cluster(self.si, c)

    def get_cluster(self, name):
        for cluster in self.get_clusters():
            if cluster.name() == name:
                return cluster
        return None

    def get_dvs_by_name(self, name):
        vmgr = self.si.RetrieveContent().viewManager
        invtvw = vmgr.CreateContainerView(
            container=self.get_root_folder(self.si),
            type=[vim.VmwareDistributedVirtualSwitch],
            recursive=True)
        for dvs in invtvw.view:
            if dvs.name == name:
                return DistributedVirtualSwitch(self.si, dvs)
        return None

    def create_dvs(self, spec):
        dvs_task = self.dc.networkFolder.CreateDVS_Task(spec)
        task.WaitForTask(task=dvs_task, si=self.si)
        return self.get_dvs_by_name(spec.configSpec.name)

    def get_datastores(self, ds_type=None):
        ds_list = self.dc.datastore
        if ds_type:
            from utils import DS_TYPE
            ds_type = ds_type.upper()
            if ds_type in DS_TYPE:
                return [DataStore(self.si, ds) for ds in ds_list
                        if ds.summary.type == ds_type]
            else:
                print "Invalid storage type: " + ds_type
                return None
        else:
            return [DataStore(self.si, ds) for ds in ds_list]

    def get_clusters(self):
        child_entitys = self.dc.hostFolder.childEntity
        return [Cluster(self.si, cluster) for cluster in child_entitys
                if isinstance(cluster, vim.ClusterComputeResource)]


class Cluster(ManagedObject):

    def __init__(self, si, cluster):
        if not isinstance(cluster, vim.ClusterComputeResource):
            raise TypeError("Not a vim.ClusterComputeResource object")
        self.si = si
        self.cluster = cluster

    def name(self):
        return self.cluster.name

    def add_host(self, hostConnectSpec):
        """Adds host to a cluster.

        @param hostConnectSpec: vim.host.ConnectSpec
        """

        hosttask = self.cluster.AddHost_Task(
            spec=hostConnectSpec,
            asConnected=True)
        task.WaitForTask(task=hosttask, si=self.si)

    def get_hosts(self):
        return [Host(self.si, host) for host in self.cluster.host]

    def enable_drs(self, enable=True):
        spec = vim.cluster.ConfigSpec(
            drsConfig=vim.cluster.DrsConfigInfo(enabled=enable))
        rcfg_task = self.cluster.ReconfigureCluster_Task(
            spec=spec, modify=True)
        task.WaitForTask(task=rcfg_task, si=self.si)

    def enable_ha(self, enable=True):
        spec = vim.cluster.ConfigSpec(
            dasConfig=vim.cluster.DasConfigInfo(enabled=enable))
        rcfg_task = self.cluster.ReconfigureCluster_Task(
            spec=spec, modify=True)
        task.WaitForTask(task=rcfg_task, si=self.si)

    @property
    def moid(self):
        return self.cluster._moId


class Host(ManagedObject):

    def __init__(self, si, host_system):
        if not isinstance(host_system, vim.HostSystem):
            raise TypeError("Not a vim.HostSystem object")
        self.si = si
        self.host_system = host_system

    def name(self):
        return self.host_system.name

    def get_datastore_by_name(self, name):
        for ds in self.host_system.datastore:
            if ds.name == name:
                return DataStore(self.si, ds)
        return None

    def get_datastores(self):
        return [DataStore(self.si, ds) for ds in self.host_system.datastore]

    def get_vms(self):
        return [VM(self.si, vm) for vm in self.host_system.vm]

    def config_vmotion(self, nic_num=0):
        if not self.host_system.capability.vmotionSupported:
            print 'Host {} not support vMotion.'.format(self.name())
            return
        vmotion_manager = self.host_system.configManager.vmotionSystem
        nic_list = vmotion_manager.netConfig.candidateVnic
        if nic_list is None:
            print 'No candidate virtual nic device found for vMotion.'
            return
        device = None
        for nic in nic_list:
            if nic.device == ('vmk' + str(nic_num)):
                device = nic.device
                break
        if device:
            print('Host {} enable vMotion on vnic {}.'.format(self.name(), device))
            vmotion_manager.SelectVnic(device)
        else:
            cand_nic_num = nic_list[0].device.replace('vmk', '')
            print 'Invalid candidate virtual nic number {} selected. ' \
                  'Candidate nic number: {}'.format(nic_num, cand_nic_num)

    def enable_ssh(self, enable=True):
        service_manager = self.host_system.configManager.serviceSystem
        if enable:
            print "Starting ssh service on " + self.host_system.name
            service_manager.StartService(id='TSM-SSH')
        else:
            print "Stopping ssh service on " + self.host_system.name
            service_manager.StopService(id='TSM-SSH')

    def enable_ntp(self, ntp):
        # Config NTP servers
        ntp_spec = vim.host.NtpConfig(server=ntp)
        time_config = vim.HostDateTimeConfig(ntpConfig=ntp_spec)
        time_manager = self.host_system.configManager.dateTimeSystem
        time_manager.UpdateDateTimeConfig(config=time_config)
        # Start NTP service
        service_manager = self.host_system.configManager.serviceSystem
        print "Starting ntpd on " + self.host_system.name
        service_manager.StartService(id='ntpd')

    def add_license(self, license_key):
        license_asg_manager = self.si.RetrieveContent()\
            .licenseManager.licenseAssignmentManager
        print 'Assign license to host {}.'.format(self.host_system.name)
        license_asg_manager.UpdateAssignedLicense(
            entity=self.host_system._moId, licenseKey=license_key)

    def add_nfs_datastore(self, ds_spec):
        if not self.host_system.capability.nfsSupported:
            print("Host {} not support nfs datastore.".format(self.name()))
            return
        print 'Add NFS {}:{} to host {}.'.format(
            ds_spec.remoteHost, ds_spec.remotePath, self.host_system.name)
        self.host_system.configManager.datastoreSystem\
            .CreateNasDatastore(ds_spec)

    def config_services(self, service_names, action='start'):
        from utils import SERVICES
        action_list = ['start', 'stop']
        action = action.lower()
        if action not in action_list:
            print 'Action {} not support yet.'.format(action)
            return
        service_list = service_names.strip().split(',')
        service_manager = self.host_system.configManager.serviceSystem
        for service in service_list:
            service = service.strip()
            if service in SERVICES:
                if action == 'start':
                    print "Starting {} on {}.".format(service, self.host_system.name)
                    service_manager.StartService(id=service)
                elif action == 'stop':
                    print "Stopping {} on {}.".format(service, self.host_system.name)
                    service_manager.StopService(id=service)
            else:
                print "Not support config service {} on {} yet."\
                    .format(service, self.host_system.name)

    def config_firewall(self, rule_names, action='enable'):
        from utils import RULES
        action_list = ['enable', 'disable']
        action = action.lower()
        if action not in action_list:
            print 'Action {} not support yet.'.format(action)
            return
        rule_list = rule_names.strip().split(',')
        fw_manager = self.host_system.configManager.firewallSystem
        for rule in rule_list:
            rule = rule.strip()
            if rule in RULES:
                if action == 'enable':
                    print "Enable rule {} on {}.".format(rule, self.host_system.name)
                    fw_manager.EnableRuleset(id=rule)
                elif action == 'disable':
                    print "Disable rule {} on {}.".format(rule, self.host_system.name)
                    fw_manager.DisableRuleset(id=rule)
            else:
                print "Not support config rule {} on {} yet."\
                    .format(rule, self.host_system.name)

    def config_autostart(self, vm_list):
        as_manager = self.host_system.configManager.autoStartManager
        as_config = vim.host.AutoStartManager.Config()
        power_info_list = []
        vms = self.get_vms()
        vm_names = [vm.name() for vm in vms]
        for vm_name in vm_list:
            if vm_name not in vm_names:
                print 'VM {} not on host {}.'.format(vm_name, self.name())
                vm_list.remove(vm_name)
        for vm in vms:
            if vm.name() in vm_list:
                power_info = vim.host.AutoStartManager.AutoPowerInfo()
                power_info.key = vm.vm
                power_info.startAction = 'powerOn'
                power_info.stopAction = 'powerOff'
                power_info.startDelay = -1
                power_info.stopDelay = -1
                power_info.startOrder = vm_list.index(vm.name()) + 1
                power_info.waitForHeartbeat =\
                    vim.host.AutoStartManager.AutoPowerInfo\
                        .WaitHeartbeatSetting().systemDefault
                power_info_list.append(power_info)
        as_config.powerInfo = power_info_list
        as_manager.ReconfigureAutostart(as_config)

    def maintenance(self, action='enter'):
        actions = ['enter', 'exit']
        action = action.lower()
        if action not in actions:
            print 'Action {} not support on host {}'\
                .format(action, self.host_system.name)
            return
        print 'Host {} {} maintenance mode.'.format(self.host_system.name,
                                                     action)
        if action == 'enter':
            main_task = self.host_system.EnterMaintenanceMode(0)
        else:
            main_task = self.host_system.ExitMaintenanceMode(0)
        task.WaitForTask(task=main_task, si=self.si)


class VM(ManagedObject):

    def __init__(self, si, vm):
        if not isinstance(vm, vim.VirtualMachine):
            raise TypeError("Not a vim.VirtualMachine object")
        self.si = si
        self.vm = vm

    # TODO(a): refactor ManagedObject class, override __getattr__
    # to retrive properties of managed object (dc, cluster, vm, ...)
    def ip(self):
        return self.vm.summary.guest.ipAddress

    def add_nic(self, nic_type, net_name, net_type):

        devices = []
        nicspec = vim.vm.device.VirtualDeviceSpec()

        nicspec.operation = vim.vm.device.VirtualDeviceSpec.Operation.add
        # For now hard code change it to to use string nic_type
        nicspec.device = vim.vm.device.VirtualVmxnet3()
        nicspec.device.wakeOnLanEnabled = True
        nicspec.device.deviceInfo = vim.Description()

        # Configuration for DVPortgroups
        if net_type == "dvs":
            pg_obj = self.get_obj(self.si,
                                  [vim.dvs.DistributedVirtualPortgroup],
                                  net_name)
            dvs_port_connection = vim.dvs.PortConnection()
            dvs_port_connection.portgroupKey = pg_obj.key
            dvs_port_connection.switchUuid = pg_obj.config.\
                distributedVirtualSwitch.uuid
            nicspec.device.backing = vim.vm.device.VirtualEthernetCard.\
                DistributedVirtualPortBackingInfo()
            nicspec.device.backing.port = dvs_port_connection
        else:
            # Configuration for Standard switch port groups
            nicspec.device.backing = vim.vm.device.\
                VirtualEthernetCard.NetworkBackingInfo()
            nicspec.device.backing.network = self.get_obj(self.si,
                                                          [vim.Network],
                                                          net_name)
            nicspec.device.backing.deviceName = net_name

        nicspec.device.connectable = vim.vm.device.VirtualDevice.ConnectInfo()
        nicspec.device.connectable.startConnected = True
        nicspec.device.connectable.allowGuestControl = True

        devices.append(nicspec)
        vmconf = vim.vm.ConfigSpec(deviceChange=devices)

        reconfig_task = self.vm.ReconfigVM_Task(vmconf)
        task.WaitForTask(task=reconfig_task, si=self.si)

    def name(self):
        return self.vm.name

    def get_state(self):
        state = self.vm.runtime.powerState
        return state

    def power(self, action='on'):
        actions = ['on', 'off']
        action = action.lower()
        if action not in actions:
            print 'Action {} not support on vm {}'.format(action, self.name())
            return
        print 'VM {} power {}.'.format(self.name(), action)
        if action == 'on':
            power_task = self.vm.PowerOn()
        else:
            power_task = self.vm.PowerOff()
        task.WaitForTask(task=power_task, si=self.si)

    def reset(self):
        reset_task = self.vm.Reset()
        task.WaitForTask(task=reset_task, si=self.si)

    def rebootvm(self):
        self.vm.RebootGuest()

    def destroy(self):
        destroy_task = self.vm.Destroy()
        task.WaitForTask(task=destroy_task, si=self.si)

    def unregister(self):
        self.vm.Unregister()

    def clone(self, name):
        relocate_spec = vim.vm.RelocateSpec()
        relocate_spec.pool = self.vm.resourcePool
        clone_spec = vim.vm.CloneSpec(powerOn=False,
                                      template=False,
                                      location=relocate_spec,
                                      customization=None)
        clone_task = self.vm.Clone(self.vm.parent, name, clone_spec)
        task.WaitForTask(task=clone_task, si=self.si)

    def snapshot(self, snap_name):
        snapshot_task = self.vm.CreateSnapshot(snap_name, snap_name, True, True)
        task.WaitForTask(task=snapshot_task, si=self.si)

    def migrate_host_datastore(self, dest_host, dest_datastore):
        # Support change both host and datastore
        vm_relocate_spec = vim.vm.RelocateSpec()
        vm_relocate_spec.host = dest_host.host_system
        vm_relocate_spec.pool = self.vm.resourcePool
        vm_relocate_spec.datastore = dest_datastore.ds
        print "Migrating {} to datastore {} on destination host {}."\
            .format(self.vm.name,
                    dest_datastore.ds.name,
                    dest_host.host_system.name)
        vmotion_task = self.vm.Relocate(spec=vm_relocate_spec)
        task.WaitForTask(task=vmotion_task, si=self.si)

    def get_datastores(self):
        return [DataStore(self.si, ds) for ds in self.vm.datastore]

    def get_host(self):
        return Host(self.si, self.vm.runtime.host)

    def get_size(self):
        disks = self.vm.storage.perDatastoreUsage
        size = 0L
        for disk in disks:
            size += disk.committed + disk.uncommitted
        return size / 1024 / 1024 / 1024


class DataStore(ManagedObject):
    B2G = 1024*1024*1024

    def __init__(self, si, ds):
        if not isinstance(ds, vim.Datastore):
            raise TypeError("Not a vim.Datastore object")
        self.si = si
        self.ds = ds

    def name(self):
        return self.ds.name

    def get_hosts(self):
        # Host list connect this ds
        return [Host(self.si, host) for host in self.ds.host]

    def get_info(self):
        return self.ds.summary

    def get_freespace(self):
        # GB
        return self.get_info().freeSpace / self.B2G

    def get_capacity(self):
        # GB
        return self.get_info().capacity / self.B2G

    def get_vms(self):
        return [VM(self.si, vm) for vm in self.ds.vm]

    @property
    def moid(self):
        return self.ds._moId


class DistributedVirtualSwitch(ManagedObject):
    def __init__(self, si, dvs):
        if not isinstance(dvs, vim.VmwareDistributedVirtualSwitch):
            raise TypeError("Not a vim.VmwareDistributedVirtualSwitch object")
        self.si = si
        self.dvs = dvs

    def name(self):
        return self.dvs.name

    def config(self):
        return self.dvs.config

    def get_portgroup(self, pg_name):
        return self.get_obj(self.si, [vim.dvs.DistributedVirtualPortgroup], pg_name)

    def add_portgroup(self, spec):
        pg_task = self.dvs.AddDVPortgroup_Task([spec])
        task.WaitForTask(task=pg_task, si=self.si)
        return pg_task.info.result

    def reconfig_dvs(self, spec):
        dvs_config_task = self.dvs.ReconfigureDvs_Task(spec)
        task.WaitForTask(task=dvs_config_task, si=self.si)
        return dvs_config_task.info.result

    @property
    def moid(self):
        return self.dvs._moId


class Network(ManagedObject):
    def __init__(self, si, net):
        if not isinstance(net, vim.Network):
            raise TypeError("Not a vim.Network object")
        self.si = si
        self.net = net

    def name(self):
        return self.net.name

    def destroy(self):
        destroy_task = self.net.Destroy()
        task.WaitForTask(task=destroy_task, si=self.si)


class Folder(ManagedObject):
    def __init__(self, si, folder):
        if not isinstance(folder, vim.Folder):
            raise TypeError("Not a vim.Folder object")
        self.si = si
        self.folder = folder

    def name(self):
        return self.folder.name

    def destroy(self):
        destroy_task = self.folder.Destroy()
        task.WaitForTask(task=destroy_task, si=self.si)


class Vapp(ManagedObject):
    def __init__(self, si, vapp):
        if not isinstance(vapp, vim.VirtualApp):
            raise TypeError("Not a vim.VirtualApp object")
        self.si = si
        self.vapp = vapp

    def poweroff(self):
        poweroff_task = self.vapp.PowerOff(force=True)
        task.WaitForTask(task=poweroff_task, si=self.si)

    def destroy(self):
        destroy_task = self.vapp.Destroy()
        task.WaitForTask(task=destroy_task, si=self.si)

    def get_state(self):
        state = self.vapp.summary.vAppState
        return state

    def poweron(self):
        poweron_task = self.vapp.PowerOn()
        task.WaitForTask(task=poweron_task, si=self.si)