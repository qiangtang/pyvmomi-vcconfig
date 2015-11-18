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
    def get_datacenter(self, name):
        """Returns a reference to datacenter in the root folder.

        @param name: name of the datacenter
        @return returns Datacenter instance
        """
        vmgr = self.si.RetrieveContent().viewManager
        invtvw = vmgr.CreateContainerView(
            container=self.get_root_folder(self.si),
            type=[vim.Datacenter],
            recursive=True)
        dcs = [dc for dc in invtvw.view if dc.name == name]
        return Datacenter(self.si, dcs[0]) if len(dcs) > 0 else None

    @requires_connection
    def get_vm_by_name(self, name, type="vm"):
        """Returns a reference to vm by its name.

        @param name: name of the vm
        @return returns VirtualMachine instance
        """
        vmgr = self.si.RetrieveContent().viewManager
        invtvw = vmgr.CreateContainerView(
            container=self.get_root_folder(self.si),
            type=[vim.VirtualMachine],
            recursive=True)
        vms = [vm for vm in invtvw.view if vm.name == name]
        return VM(self.si, vms[0]) if len(vms) > 0 else None

    @requires_connection
    def get_datastore(self, name=None):
        vmgr = self.si.RetrieveContent().viewManager
        invtvw = vmgr.CreateContainerView(
            container=self.get_root_folder(self.si),
            type=[vim.Datastore],
            recursive=True)
        if name:
            ds = [ds for ds in invtvw.view if ds.name == name]
        else:
            ds = invtvw.view

        return DataStore(self.si, ds[0]) if ds else None

    @requires_connection
    def get_hosts(self):
        vmgr = self.si.RetrieveContent().viewManager
        invtvw = vmgr.CreateContainerView(
            container=self.get_root_folder(self.si),
            type=[vim.HostSystem],
            recursive=True)
        return [Host(self.si, h) for h in invtvw.view]

    @requires_connection
    def get_host_by_name(self, name):
        vmgr = self.si.RetrieveContent().viewManager
        invtvw = vmgr.CreateContainerView(
            container=self.get_root_folder(self.si),
            type=[vim.HostSystem],
            recursive=True)
        host = None
        for h in invtvw.view:
            if h.name == name:
                host = h
                break
        return Host(self.si, host) if host else None

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
        vapp = None
        for v in invtvw.view:
            if name in v.name:
                vapp = v
                break
        return Vapp(self.si, vapp) if vapp else None

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


class Datacenter(ManagedObject):

    def __init__(self, si, dc):
        if not isinstance(dc, vim.Datacenter):
            raise TypeError("Not a vim.Datacenter object")
        self.dc = dc
        self.si = si

    def create_cluster(self, name, config=vim.cluster.ConfigSpecEx()):
        """Creates cluster.

        @param name: name of the cluster
        @param config: vim.cluster.ConfigSpecEx
        """

        hostFolder = self.dc.hostFolder
        c = hostFolder.CreateClusterEx(name, config)
        return Cluster(self.si, c)

    def get_cluster(self, name):
        vmgr = self.si.RetrieveContent().viewManager
        invtvw = vmgr.CreateContainerView(
            container=self.get_root_folder(self.si),
            type=[vim.ClusterComputeResource],
            recursive=True)
        clusters = [c for c in invtvw.view if c.name == name]
        return Cluster(self.si, clusters[0]) if len(clusters) > 0 else None

    def get_dvs_by_name(self, name=None):
        vmgr = self.si.RetrieveContent().viewManager
        invtvw = vmgr.CreateContainerView(
            container=self.get_root_folder(self.si),
            type=[vim.VmwareDistributedVirtualSwitch],
            recursive=True)
        if name:
            dvs = [dvs for dvs in invtvw.view if dvs.name == name]
        else:
            dvs = invtvw.view
        return DistributedVirtualSwitch(self.si, dvs[0]) if dvs else None

    def create_dvs(self, spec):
        dvs_task = self.dc.networkFolder.CreateDVS_Task(spec)
        task.WaitForTask(task=dvs_task, si=self.si)
        return self.get_dvs_by_name(spec.configSpec.name)


class Cluster(ManagedObject):

    def __init__(self, si, cluster):
        if not isinstance(cluster, vim.ClusterComputeResource):
            raise TypeError("Not a vim.ClusterComputeResource object")
        self.si = si
        self.cluster = cluster

    def add_host(self, hostConnectSpec):
        """Adds host to a cluster.

        @param hostConnectSpec: vim.host.ConnectSpec
        """

        hosttask = self.cluster.AddHost_Task(
            spec=hostConnectSpec,
            asConnected=True)
        task.WaitForTask(task=hosttask, si=self.si)

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
        print 'Add NFS {}:{} to host {}.'.format(
            ds_spec.remoteHost, ds_spec.remotePath, self.host_system.name)
        self.host_system.configManager.datastoreSystem\
            .CreateNasDatastore(ds_spec)


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

    def poweroff(self):
        poweroff_task = self.vm.PowerOff()
        task.WaitForTask(task=poweroff_task, si=self.si)

    def destroy(self):
        destroy_task = self.vm.Destroy()
        task.WaitForTask(task=destroy_task, si=self.si)

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


class DataStore(ManagedObject):
    def __init__(self, si, ds):
        if not isinstance(ds, vim.Datastore):
            raise TypeError("Not a vim.Datastore object")
        self.si = si
        self.ds = ds

    def name(self):
        return self.ds.name

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