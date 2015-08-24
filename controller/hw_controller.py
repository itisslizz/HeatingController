"""
This module will communicate with the
Honeywell Thermostats using coap
"""
import asyncio
from aiocoap import *




@asyncio.coroutine
def coap_get_temperature(future, mac):
    protocol = yield from Context.create_client_context()
    request = Message(code=GET)
    request.set_request_uri('coap://[fdfd::' + mac + ']/sensors/temperature')
    try:
        response = yield from protocol.request(request).response
    except Exception as e:
        print('Failed to fetch resource:')
        print(e)
        future.set_result(('error').encode('utf-8'))
    else:
        future.set_result(response.payload)


@asyncio.coroutine
def coap_get_setpoint(future, mac):
    protocol = yield from Context.create_client_context()
    request = Message(code=GET)
    request.set_request_uri('coap://[fdfd::' + mac + ']/set/target')
    try:
        response = yield from protocol.request(request).response
    except Exception as e:
        print('Failed to fetch resource:')
        print(e)
        future.set_result(("error").encode('utf-8'))
    else:
        future.set_result(response.payload)


@asyncio.coroutine
def coap_put_setpoint(setpoint, mac):

    context = yield from Context.create_client_context()

    payload = str(setpoint).encode('utf-8')
    request = Message(code=PUT, payload=payload)
    request.opt.uri_host = '[fdfd::' + mac + ']'
    request.opt.uri_path = ("set", "target")

    try:
        response = yield from context.request(request).response
    except Exception as e:
        print("Failed to put the setpoint")
        print(e)
    # print('Result: %s\n%r'%(response.code, response.payload))


def put_setpoint(mac, setpoint):
    asyncio.get_event_loop().run_until_complete(coap_put_setpoint(setpoint, mac))


def get_setpoint(mac):
    loop = asyncio.get_event_loop()
    future = asyncio.Future()
    asyncio.async(coap_get_setpoint(future, mac))
    loop.run_until_complete(future)
    response = future.result().decode('utf-8')
    return response


def get_temperature(mac):
    loop = asyncio.get_event_loop()
    future = asyncio.Future()
    asyncio.async(coap_get_temperature(future, mac))
    loop.run_until_complete(future)
    response = future.result().decode('utf-8')
    return response

