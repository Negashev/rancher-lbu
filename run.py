#!/usr/bin/python3
import aiohttp
import os
import json
import copy

from aiohttp import BasicAuth
from japronto import Application

V1 = 'v1'
V2_BETA = 'v2-beta'
CI_ENVIRONMENT_SLUG = os.getenv('CI_ENVIRONMENT_SLUG', 'rlbu-url-not-set')
CI_ENVIRONMENT_SLUG = os.getenv('RLBU_ENVIRONMENT', CI_ENVIRONMENT_SLUG)


async def get(url):
    """Sends get request"""
    async with aiohttp.ClientSession(
            auth=BasicAuth(os.getenv('RANCHER_ACCESS_KEY'), os.getenv('RANCHER_SECRET_KEY'))) as session:
        async with session.get(f"{os.getenv('RANCHER_URL')}/{url}") as response:
            return await response.json()


async def put(url, payload):
    """Sends put request"""
    async with aiohttp.ClientSession(
            auth=BasicAuth(os.getenv('RANCHER_ACCESS_KEY'), os.getenv('RANCHER_SECRET_KEY'))) as session:
        async with session.put(f"{os.getenv('RANCHER_URL')}/{url}", data=json.dumps(payload).encode()) as response:
            return await response.json()


async def __get_lb_service(service_id):
    return await get(f'{V2_BETA}/loadbalancerservices/{service_id}')


def merge(left, right, path=None):
    """Merge dicts"""

    if path is None:
        path = []
    for key in right:
        if key in left:
            if isinstance(left[key], dict) and isinstance(right[key], dict):
                merge(left[key], right[key], path + [str(key)])
            elif left[key] == right[key]:
                pass  # same leaf value
            elif isinstance(left[key], list) and isinstance(right[key], list):
                for item in right[key]:
                    if item not in left[key]:
                        left[key].append(item)
            else:
                raise Exception('Conflict at %s' %
                                '.'.join(path + [str(key)]))
        else:
            left[key] = right[key]
    return left


async def update_load_balancer_service(request):
    """Update load balancer target"""
    load_balancer_id = os.getenv('RANCHER_LB_ID')
    lb_config = await __get_lb_service(load_balancer_id)
    seen = []
    new_portRules = []
    old_portRules = copy.deepcopy(lb_config["lbConfig"]["portRules"])
    for d in old_portRules:
        t = d.copy()
        drop = True
        if 'serviceId' in t:
            if t['serviceId'] is not None:
                drop = False
        priority_not_exist = False
        if 'path' in t:
            if t['path'] is None:
                del t['path']
                priority_not_exist = True
        if 'selector' in t:
            if t['selector'] is None:
                del t['selector']
                priority_not_exist = True
            else:
                drop = False
        if 'backendName' in t:
            if t['backendName'] is None:
                del t['backendName']
                priority_not_exist = True
        if priority_not_exist:
            del t['priority']
        if t not in seen and not drop:
            seen.append(t)
            new_portRules.append(d)

    lb_config["lbConfig"]["portRules"] = new_portRules

    payload = merge(lb_config,
                    {"lbConfig":
                         {"portRules": [{"protocol": os.getenv('RANCHER_LB_PROTOCOL', "http"),
                                         "type": os.getenv('RANCHER_LB_TYPE', "portRule"),
                                         "hostname": "{}-{}.{}".format(os.getenv('CI_PROJECT_PATH_SLUG'),
                                                                       CI_ENVIRONMENT_SLUG,
                                                                       os.getenv('ENV_DOMAIN')),
                                         "sourcePort": int(os.getenv('EXTERNAL_PORT', 80)),
                                         "targetPort": int(os.getenv('INTERNAL_PORT', 80)),
                                         "serviceId": request.match_dict['service_id']}
                                        ]
                          }
                     })
    end_point = f"{V2_BETA}/projects/{os.getenv('RANCHER_ENVIRONMENT')}/loadbalancerservices/{load_balancer_id}"
    data = await put(end_point, payload)
    print(data['id'])
    hostname = "{}-{}.{}:{}".format(
        os.getenv('CI_PROJECT_PATH_SLUG'),
        CI_ENVIRONMENT_SLUG,
        os.getenv('ENV_DOMAIN'),
        os.getenv('EXTERNAL_PORT', 80)
    )
    print(f"update lb for {hostname}")
    return request.Response(text=hostname, mime_type="text/html")


app = Application()
app.router.add_route('/{service_id}', update_load_balancer_service)
app.run(port=int(os.getenv('RLBU_PORT', 80)))
