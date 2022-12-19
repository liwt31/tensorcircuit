"""
main entrypoints of cloud module
"""

from typing import Any, List, Optional, Dict, Union
from base64 import b64decode, b64encode
from functools import partial
import json
import os
import sys

from .abstraction import Provider, Device, Task, sep, sep2
from . import tencent
from . import local

package_name = "tensorcircuit"
thismodule = sys.modules[__name__]


default_provider = Provider.from_name("tencent")
avail_providers = ["tencent", "local"]


def list_providers() -> List[Provider]:
    """
    list all providers that tensorcircuit supports

    :return: _description_
    :rtype: List[Provider]
    """
    return [get_provider(s) for s in avail_providers]


def set_provider(
    provider: Optional[Union[str, Provider]] = None, set_global: bool = True
) -> Provider:
    """
    set default provider for the program

    :param provider: _description_, defaults to None
    :type provider: Optional[Union[str, Provider]], optional
    :param set_global: whether set, defaults to True,
        if False, equivalent to ``get_provider``
    :type set_global: bool, optional
    :return: _description_
    :rtype: Provider
    """
    if provider is None:
        provider = default_provider
    provider = Provider.from_name(provider)
    if set_global:
        for module in sys.modules:
            if module.startswith(package_name):
                setattr(sys.modules[module], "default_provider", provider)
    return provider


set_provider()
get_provider = partial(set_provider, set_global=False)

default_device = Device.from_name("tencent::simulator:tc")


def set_device(
    provider: Optional[Union[str, Provider]] = None,
    device: Optional[Union[str, Device]] = None,
    set_global: bool = True,
) -> Device:
    """
    _summary_

    :param provider: provider of the device, defaults to None
    :type provider: Optional[Union[str, Provider]], optional
    :param device: the device, defaults to None
    :type device: Optional[Union[str, Device]], optional
    :param set_global: whether set, defaults to True,
        if False, equivalent to ``get_device``, defaults to True
    :type set_global: bool, optional
    :return: _description_
    :rtype: Device
    """
    if provider is not None and device is None:
        provider, device = None, provider
    if device is None and provider is not None:
        raise ValueError("Please specify the device apart from the provider")
    if device is None:
        device = default_device

    if isinstance(device, str):
        if len(device.split(sep)) > 1:
            device = Device(device, provider)
        else:
            if provider is None:
                provider = get_provider()
            device = Device(device, provider)
    else:
        if provider is None:
            provider = get_provider()
        device = Device.from_name(device, provider)

    if set_global:
        for module in sys.modules:
            if module.startswith(package_name):
                setattr(sys.modules[module], "default_device", device)
    return device


set_device()
get_device = partial(set_device, set_global=False)


def b64encode_s(s: str) -> str:
    return b64encode(s.encode("utf-8")).decode("utf-8")


def b64decode_s(s: str) -> str:
    return b64decode(s.encode("utf-8")).decode("utf-8")


saved_token: Dict[str, Any] = {}


def set_token(
    token: Optional[str] = None,
    provider: Optional[Union[str, Provider]] = None,
    device: Optional[Union[str, Device]] = None,
    cached: bool = True,
) -> Dict[str, Any]:
    global saved_token
    homedir = os.path.expanduser("~")
    authpath = os.path.join(homedir, ".tc.auth.json")
    if provider is None:
        provider = default_provider
    provider = Provider.from_name(provider)
    if device is not None:
        device = Device.from_name(device, provider)
    # if device is None:
    #     device = default_device

    if token is None:
        if cached and os.path.exists(authpath):
            with open(authpath, "r") as f:
                file_token = json.load(f)
                file_token = {k: b64decode_s(v) for k, v in file_token.items()}
                # file_token = backend.tree_map(b64decode_s, file_token)
        else:
            file_token = {}
        file_token.update(saved_token)
        saved_token = file_token
    else:  # with token
        if device is None:
            if provider is None:
                provider = Provider.from_name("tencent")
            added_token = {provider.name + sep: token}
        else:
            added_token = {provider.name + sep + device.name: token}
        saved_token.update(added_token)

    if cached:
        # file_token = backend.tree_map(b64encode_s, saved_token)
        file_token = {k: b64encode_s(v) for k, v in saved_token.items()}

        with open(authpath, "w") as f:
            json.dump(file_token, f)

    return saved_token


set_token()


def get_token(
    provider: Optional[Union[str, Provider]] = None,
    device: Optional[Union[str, Device]] = None,
) -> Optional[str]:
    if provider is None:
        provider = default_provider
    provider = Provider.from_name(provider)
    if device is not None:
        device = Device.from_name(device, provider)
    target = provider.name + sep
    if device is not None:
        target = target + device.name
    for k, v in saved_token.items():
        if k == target:
            return v  # type: ignore
    return None


# token json structure
# {"tencent::": token1, "tencent::20xmon":  token2}


def list_devices(
    provider: Optional[Union[str, Provider]] = None, token: Optional[str] = None
) -> Any:
    if provider is None:
        provider = default_provider
    provider = Provider.from_name(provider)
    if token is None:
        token = provider.get_token()
    if provider.name == "tencent":
        return tencent.list_devices(token)
    elif provider.name == "local":
        return local.list_devices(token)
    else:
        raise ValueError("Unsupported provider: %s" % provider.name)


def list_properties(
    provider: Optional[Union[str, Provider]] = None,
    device: Optional[Union[str, Device]] = None,
    token: Optional[str] = None,
) -> Dict[str, Any]:
    if provider is not None and device is None:
        provider, device = None, provider
    if device is None:
        device = default_device
    device = Device.from_name(device, provider)
    if provider is None:
        provider = device.provider

    if token is None:
        token = device.get_token()  # type: ignore
    if provider.name == "tencent":  # type: ignore
        return tencent.list_properties(device, token)
    else:
        raise ValueError("Unsupported provider: %s" % provider.name)  # type: ignore


def get_task(
    taskid: str,
    provider: Optional[Union[str, Provider]] = None,
    device: Optional[Union[str, Device]] = None,
) -> Task:
    if provider is not None and device is None:
        provider, device = None, provider
    if device is not None:  # device can be None for identify tasks
        device = Device.from_name(device, provider)
    elif len(taskid.split(sep2)) > 1:
        device = Device(taskid.split(sep2)[0])
        taskid = taskid.split(sep2)[1]
    return Task(taskid, device=device)


def get_task_details(
    taskid: Union[str, Task], token: Optional[str] = None
) -> Dict[str, Any]:
    if isinstance(taskid, str):
        task = Task(taskid)
    else:
        task = taskid
    if task.device is not None:
        device = task.device
    else:
        device = default_device
    if token is None:
        token = device.get_token()
    provider = device.provider

    if provider.name == "tencent":
        return tencent.get_task_details(task, device, token)  # type: ignore
    elif provider.name == "local":
        return local.get_task_details(task, device, token)  # type: ignore
    else:
        raise ValueError("Unsupported provider: %s" % provider.name)  # type: ignore


def submit_task(
    provider: Optional[Union[str, Provider]] = None,
    device: Optional[Union[str, Device]] = None,
    token: Optional[str] = None,
    **task_kws: Any,
) -> List[Task]:
    if device is None:
        device = get_device()
    if isinstance(device, str):
        if len(device.split(sep)) > 1:
            device = Device(device, provider)
        else:
            if provider is None:
                provider = get_provider()
            device = Device(device, provider)
    if provider is None:
        provider = device.provider

    if token is None:
        token = device.get_token()  # type: ignore

    if provider.name == "tencent":  # type: ignore
        return tencent.submit_task(device, token, **task_kws)  # type: ignore
    elif provider.name == "local":  # type: ignore
        return local.submit_task(device, token, **task_kws)  # type: ignore
    else:
        raise ValueError("Unsupported provider: %s" % provider.name)  # type: ignore


def resubmit_task(
    task: Optional[Union[str, Task]],
    token: Optional[str] = None,
) -> Task:
    if isinstance(task, str):
        task = Task(task)
    device = task.get_device()  # type: ignore
    if token is None:
        token = device.get_token()
    provider = device.provider

    if provider.name == "tencent":  # type: ignore
        return tencent.resubmit_task(task, token)  # type: ignore
    else:
        raise ValueError("Unsupported provider: %s" % provider.name)  # type: ignore


def remove_task(
    task: Optional[Union[str, Task]],
    token: Optional[str] = None,
) -> Task:
    if isinstance(task, str):
        task = Task(task)
    device = task.get_device()  # type: ignore
    if token is None:
        token = device.get_token()
    provider = device.provider

    if provider.name == "tencent":  # type: ignore
        return tencent.remove_task(task, token)  # type: ignore
    else:
        raise ValueError("Unsupported provider: %s" % provider.name)  # type: ignore


def list_tasks(
    provider: Optional[Union[str, Provider]] = None,
    device: Optional[Union[str, Device]] = None,
    token: Optional[str] = None,
    **filter_kws: Any,
) -> List[Task]:
    if provider is None:
        provider = default_provider
    provider = Provider.from_name(provider)
    if token is None:
        token = provider.get_token()  # type: ignore
    if device is not None:
        device = Device.from_name(device)
    if provider.name == "tencent":  # type: ignore
        return tencent.list_tasks(device, token, **filter_kws)  # type: ignore
    elif provider.name == "local":  # type: ignore
        return local.list_tasks(device, token, **filter_kws)  # type: ignore
    else:
        raise ValueError("Unsupported provider: %s" % provider.name)  # type: ignore
