'''
Send events to CoScale API
==========================

This state is useful for creating and sending events to CoScale API during state runs.

.. code-block:: yaml

    coscale-event:
        coscale.event:
            - baseurl: https://api.coscale.com/
            - accesstoken: 42c59aad-40b6-4924-9710-2d1d4a0fb632
            - appid: 00006e0e-5d0c-4633-abce-1e424f767a03
            - event_name: 'Software updates'
            - event_message: 'Updating to version 2.2'
            - event_timestamp: 0        #optional
'''

import json
import requests

def _login(accesstoken, url):
    '''
    Authentication using the Access token to get a HTTPAuthentication token from the CoScale API.

    The following parameters are required:
    accessToken
        The accessToken is used to login to the API
    url
        The url we need to access in order to get the token

    Return the HTTPAuthentication token.
    '''
    data = {'accessToken': accesstoken}
    req = requests.post(url, data=data, timeout=1)
    if req.status_code != 200:
        raise AttributeError(req.text)
    response = json.loads(req.text)
    return response['token']

def _eventpush(name, token, url):
    '''
    Create and event using the event name.

    The following parameters are required:
    name
        The event name
    token
        HTTPAuthentication token used for authentication
    url
        We create a POST request to this url to create an event

    Return request if there was an error or the event id if the request succeed
    '''
    data = {'name':			name,
            'description':	'',
            'type':			'',
            'source':		'SaltStack'}
    headers = {'HTTPAuthorization': token}
    req = requests.post(url, data=data, headers=headers, timeout=1)
    if req.status_code == 409 or req.status_code == 200:
        response = json.loads(req.text)
        return (None, response["id"])
    return (req, None)

def _eventdatapush(message, timestamp, token, url):
    '''
    Push event data using message and timestamp.

    The following parameters are required:
    message
        The actual message
    timestamp
        Unix timestamp in seconds
    token
        HTTPAuthentication token used for authentication
    url
        We create a POST request to this url to push event message

    Return request response if the request failed or None if succeed.
    '''
    data = {
        'message': 		message,
        'timestamp': 	timestamp,
        'subject':		'a'}
    headers = {'HTTPAuthorization': token}
    req = requests.post(url, data=data, headers=headers, timeout=1)
    if req.status_code != 200:
        return req
    return None

def event(baseurl, accesstoken, appid, event_name, event_message, timestamp=0):
    '''
    Deals with login, event creation and event data pushing.

    .. code-block:: yaml
        coscale-event:
            coscale.event:
                - baseurl: https://api.coscale.com/
                - accessToken: 42c59aad-40b6-4924-9710-1e424f767a03
                - appid: 00c59e0e-5d0c-4633-abce-1e4924767a03
                - event_name: 'Software updates'
                - event_message: 'Updating to version 2.2'
                - event_timestamp: 0

        The following parameters are required:

        baseurl
            The url used to create login url, post event url and post data url
        accesstoken
            The accessToken is used to login to the API
        appid
            The appid (uuid) used for API connection
        event_name
            The name of the event, this will appear in the CoScale interface
        event_message
            The message of the event, this will appear in the CoScale interface

        The following parameter is optional:
        event_timestamp
            Unix timestamp in seconds. Default is ``0``

        Return whether the event was successfully sent to the CoScale API.
    '''
    ret = {'name': event_name,
           'changes': {},
           'result': False,
           'comment': ''}

    baseurl = baseurl + 'api/v1/app/' + appid + '/'
    try:
        token = _login(accesstoken, baseurl + 'login/')
        err, event_id	= _eventpush(event_name, token, url=baseurl + 'events/')
        if err is not None:
            if err.status_code == 401:
                token = _login(accesstoken, baseurl + 'login/')
                err, event_id = _eventpush(name=event_name, token=token, url=baseurl + 'events/')
            if err.status_code not in [401, None]:
                ret['comment'] = err.text
                return ret
        url = baseurl + 'events/' + str(event_id) + '/data/'
        err = _eventdatapush(event_message, timestamp, token, url=url)
        if err is not None:
            if err.status_code == 401:
                token = _login(accesstoken, baseurl + 'login/')
                err = _eventdatapush(event_message, timestamp, token, url=url)
            if err.status_code not in [401, None]:
                ret['comment'] = err.text
                return ret
        ret['result'] = True
        ret['comment'] = 'Sent event: {0}'.format(event_name)
        return ret
    except AttributeError as err:
        ret['comment'] = err
        return ret
