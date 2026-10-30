"""Named actions a job can run. An action is a function called with the job's args as keywords."""

ACTIONS = {}


def register(name):
    def deco(fn):
        ACTIONS[name] = fn
        return fn

    return deco


@register("echo")
def echo(text=""):
    return text


@register("fail")
def fail(message="failed"):
    raise RuntimeError(message)
