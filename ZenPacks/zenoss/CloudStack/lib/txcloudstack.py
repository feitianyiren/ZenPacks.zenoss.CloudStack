###########################################################################
#
# This program is part of Zenoss Core, an open source monitoring platform.
# Copyright (C) 2011, 2012 Zenoss Inc.
#
# This program is free software; you can redistribute it and/or modify it
# under the terms of the GNU General Public License version 2 or (at your
# option) any later version as published by the Free Software Foundation.
#
# For complete information please visit: http://www.zenoss.com/oss/
#
###########################################################################

import base64
import hashlib
import hmac
import json
import urllib

from twisted.internet import defer
import twisted.web.client


__all__ = ['Client', 'capacity_type_string']


def capacity_type_string(type_id):
    """Return a string representation for the given capacity type_id.

    This list comes from the following URL:
    http://cloudstack.org/forum/6-general-discussion/7102-performance-monitoring-option-for-cloudcom.html
    """
    return {
        0: 'memory',  # bytes
        1: 'cpu',  # MHz
        2: 'primary_storage_used',  # bytes
        3: 'primary_storage_allocated',  # bytes
        4: 'public_ips',
        5: 'private_ips',
        6: 'secondary_storage',  # bytes
        }.get(type_id, 'unknown')


class Client(object):
    """CloudStack client."""

    def __init__(self, base_url, api_key, secret_key):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.secret_key = secret_key
        self._page_size = None

    def _sign(self, url):
        """Generate a signed URL for the provided url and secret key.

        The procedure for creating a signature is documented at
        http://docs.cloud.com/CloudStack_Documentation/Developer's_Guide%3A_CloudStack
        """

        base_url, query_string = url.split('?')
        msg = '&'.join(sorted(x.lower() for x in query_string.split('&')))

        signature = base64.b64encode(hmac.new(
            self.secret_key, msg=msg, digestmod=hashlib.sha1).digest())

        return '%s?%s&signature=%s' % (
            base_url, query_string, urllib.quote(signature))

    def _request_single(self, command, **kwargs):
        def process_result(result):
            data = json.loads(result)

            # For generating test data.
            # f = open('%s.json' % data.keys()[0], 'wb')
            # f.write(result)
            # f.close()

            return data

        params = kwargs
        params['command'] = command
        params['apiKey'] = self.api_key
        params['response'] = 'json'

        url = self._sign("%s/client/api?%s" % (
            self.base_url, urllib.urlencode(params)))

        return twisted.web.client.getPage(url).addCallback(process_result)

    def _get_page_size(self):
        # use listEvents to get pagesize, since every user can call it
        # but listEvents normally would not produce pagesize except in
        # error message
        # the use of 1000000 is intentional in order to generate error
        # and therefore, addErrback()
        if self._page_size is None:
            d = self._request_single(
                'listEvents', page=1, pagesize=1000000)

            return d.addErrback(self._process_page_size_error)
        else:
            return defer.succeed()

    def _process_page_size_error(self, result):
        if hasattr(result, 'value') and hasattr(result.value, 'response'):
            response = json.loads(result.value.response)
            listEventResponse = response.get('listeventsresponse', None)
            if listEventResponse:
                errorText = listEventResponse.get('errortext', None)
            if errorText and ':' in errorText:
                self._page_size = int(errorText[errorText.index(':') + 1:].strip())

    def _request_page(self, result, page, all_results, command, **kwargs):
        response_key = '%sresponse' % command.lower()

        # Need to get first page.
        if result is None:
            d = self._request_single(
                command, page=page, pagesize=self._page_size, **kwargs)

            d.addCallback(
                self._request_page, page, all_results, command, **kwargs)

            return d

        # Already have at least one page. Combine and decide if we need another.
        else:
            all_results.setdefault(response_key, {})

            for k, v in result[response_key].items():
                if k in all_results[response_key]:
                    if k == 'count':
                        all_results[response_key][k] += v
                    else:
                        all_results[response_key][k].extend(v)
                else:
                    all_results[response_key][k] = v

            # Internal hard limit of 20 pages. At this many pages responses
            # take too long to be useful. More data can be captured by
            # increasing CloudStack's API page size configuration.
            if page > 20:
                return all_results

            if result[response_key].get('count', 0) >= self._page_size:
                page += 1
                d = self._request_single(
                    command, page=page, pagesize=self._page_size, **kwargs)

                d.addCallback(
                    self._request_page, page, all_results, command, **kwargs)

                return d
            else:
                return all_results

    @defer.inlineCallbacks
    def _request(self, command, **kwargs):
        if command.startswith('list'):
            all_results = {}

            if not self._page_size:
                yield self._get_page_size()

            result = yield self._request_page(None, 0, all_results, command, **kwargs)
        else:
            result = yield self._request_single(command, **kwargs)

        defer.returnValue(result)

    def listConfigurations(self, **kwargs):
        return self._request('listConfigurations', **kwargs)

    def listDomains(self, **kwargs):
        return self._request('listDomains', **kwargs)

    def listDomainChildren(self, **kwargs):
        return self._request('listDomainChildren', **kwargs)

    def listZones(self, **kwargs):
        return self._request('listZones', **kwargs)

    def listPods(self, **kwargs):
        return self._request('listPods', **kwargs)

    def listClusters(self, **kwargs):
        return self._request('listClusters', **kwargs)

    def listHosts(self, **kwargs):
        return self._request('listHosts', **kwargs)

    def listSystemVms(self, **kwargs):
        return self._request('listSystemVms', **kwargs)

    def listRouters(self, **kwargs):
        return self._request('listRouters', **kwargs)

    def listVirtualMachines(self, **kwargs):
        return self._request('listVirtualMachines', **kwargs)

    def listCapacity(self, **kwargs):
        return self._request('listCapacity', **kwargs)

    def listAlerts(self, **kwargs):
        return self._request('listAlerts', **kwargs)

    def listEvents(self, **kwargs):
        return self._request('listEvents', **kwargs)


if __name__ == '__main__':
    import os
    import sys

    from twisted.internet import reactor
    from twisted.internet.defer import DeferredList

    client = Client(
        os.environ.get('CLOUDSTACK_URL', 'http://localhost/'),
        os.environ.get('CLOUDSTACK_APIKEY', 'asd123'),
        os.environ.get('CLOUDSTACK_SECRETKEY', 'asd123'))

    def callback(results):
        reactor.stop()

        for success, result in results:
            if success:
                from pprint import pprint
                pprint(result)
            elif hasattr(result, 'value') and hasattr(result.value, 'response'):
                print result.value.response
            else:
                print result.getErrorMessage()

    deferreds = []
    if len(sys.argv) < 2:
        deferreds.extend((
            client.listConfigurations(name='default.page.size'),
            client.listZones(available='true'),
            client.listPods(),
            client.listClusters(),
            client.listHosts(),
            client.listSystemVms(),
            client.listRouters(listAll='true'),
            client.listVirtualMachines(),
            client.listCapacity(),
            client.listAlerts(),
            client.listEvents(),
            ))
    else:
        for command in sys.argv[1:]:
            call = getattr(client, command, None)
            if call is not None:
                if command == 'listConfigurations':
                    deferreds.append(call(name='default.page.size'))
                elif command == 'listHosts':
                    deferreds.append(call(type='Routing'))
                elif command == 'listRouters':
                    deferreds.append(call(listAll='true'))
                elif command == 'listVirtualMachines':
                    deferreds.append(call(domainid='1', isrecursive=True, state='Running', listAll='true'))
                else:
                    deferreds.append(call())

    DeferredList(deferreds, consumeErrors=True).addCallback(callback)
    reactor.run()
