###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2012-2013, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from Products.ZenRelations.RelSchema import ToMany, ToManyCont, ToOne

from ZenPacks.zenoss.CloudStack import BaseComponent
from ZenPacks.zenoss.CloudStack.utils import require_zenpack


class VirtualMachine(BaseComponent):
    meta_type = portal_type = "CloudStackVirtualMachine"

    account = None
    cpu_number = None
    cpu_speed = None
    created = None
    display_name = None
    domain = None
    ha_enable = None
    memory = None
    mac_address = None
    ip_address = None
    netmask = None
    gateway = None
    root_device_type = None
    service_offering = None
    state = None
    template = None

    _properties = BaseComponent._properties + (
        {'id': 'account', 'type': 'string', 'mode': 'w'},
        {'id': 'cpu_number', 'type': 'int', 'mode': 'w'},
        {'id': 'cpu_speed', 'type': 'int', 'mode': 'w'},
        {'id': 'created', 'type': 'string', 'mode': 'w'},
        {'id': 'display_name', 'type': 'string', 'mode': 'w'},
        {'id': 'domain', 'type': 'string', 'mode': 'w'},
        {'id': 'ha_enable', 'type': 'boolean', 'mode': 'w'},
        {'id': 'memory', 'type': 'int', 'mode': 'w'},
        {'id': 'mac_address', 'type': 'string', 'mode': 'w'},
        {'id': 'ip_address', 'type': 'string', 'mode': 'w'},
        {'id': 'netmask', 'type': 'string', 'mode': 'w'},
        {'id': 'gateway', 'type': 'string', 'mode': 'w'},
        {'id': 'root_device_type', 'type': 'string', 'mode': 'w'},
        {'id': 'service_offering', 'type': 'string', 'mode': 'w'},
        {'id': 'state', 'type': 'string', 'mode': 'w'},
        {'id': 'template', 'type': 'string', 'mode': 'w'},
        )

    _relations = BaseComponent._relations + (
        ('zone', ToOne(ToManyCont,
            'ZenPacks.zenoss.CloudStack.Zone.Zone',
            'vms')
            ),

        ('host', ToOne(ToMany,
            'ZenPacks.zenoss.CloudStack.Host.Host',
            'vms')
            ),
        )

    _catalogs = {
        'VirtualMachineCatalog': {
            'deviceclass': '/CloudStack',
            'indexes': {
                'ipv4_addresses': {'type': 'keyword'},
                'mac_addresses': {'type': 'keyword'},
                },
            },
        }

    @property
    def ipv4_addresses(self):
        return (self.ip_address,)

    @property
    def mac_addresses(self):
        return (self.mac_address,)

    @classmethod
    def findByIP(cls, dmd, ipv4_addresses):
        '''
        Return the first VirtualMachine matching one of ipv4_addresses.
        '''
        return next(cls.search(
            dmd, 'VirtualMachineCatalog', ipv4_addresses=ipv4_addresses), None)

    @classmethod
    def findByMAC(cls, dmd, mac_addresses):
        '''
        Return the first VirtualMachine matching one of mac_addresses.
        '''
        return next(cls.search(
            dmd, 'VirtualMachineCatalog', mac_addresses=mac_addresses), None)

    def device(self):
        zone = self.zone()
        if not zone:
            zone = self.getPrimaryParent().getPrimaryParent()

        return zone.device()

    def setHostId(self, host_id):
        for pod in self.zone().pods():
            for cluster in pod.clusters():
                for host in cluster.hosts():
                    if host_id == host.cloudstack_id:
                        self.host.addRelation(host)
                        return

    def getHostId(self):
        host = self.host()
        if host:
            return host.cloudstack_id

    def getManagedDevice(self):
        device = self.findDevice(self.ip_address)
        if device:
            return device

        ip = self.getDmdRoot("Networks").findIp(self.ip_address)
        if ip:
            return ip.device()

    @require_zenpack('ZenPacks.zenoss.XenServer')
    def xenserver_vm(self):
        from ZenPacks.zenoss.XenServer.VIF import VIF

        vif = VIF.findByMAC(self.dmd, mac_addresses=self.mac_addresses)
        if vif:
            return vif.vm()
