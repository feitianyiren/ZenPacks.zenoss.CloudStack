###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2011, Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

from zope.interface import implements

from Products.Zuul import getFacade
from Products.ZenModel.interfaces import IDeviceLoader


class CloudStackLoader(object):
    """Device loader for CloudStack ZenPack."""

    implements(IDeviceLoader)

    def load_device(self, dmd, device_name, url, api_key, secret_key):
        return getFacade('cloudstack', dmd).add_cloudstack(
            device_name, url, api_key, secret_key)
