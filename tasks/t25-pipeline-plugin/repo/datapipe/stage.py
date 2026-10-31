from .errors import ConfigError, Reject, StageError

ON_REJECT = ("skip", "fail")


class Stage:
    """Base class of every stage.

    A run calls open(context) once before the first record, process(record) for each record, flush()
    when the input has ended and close() last, even after a failure. Plugins implement what they need
    and leave the rest alone; the pipeline and handle() take care of counting, dead letters and errors.
    """
    OPTIONS = ()    # option names the plugin understands
    REQUIRED = ()   # the ones that must be given

    def __init__(self, name, options):
        unknown = sorted(set(options) - set(self.OPTIONS) - {"on_reject"})
        if unknown:
            raise ConfigError(name, f"unknown option(s): {', '.join(unknown)}")
        missing = [opt for opt in self.REQUIRED if opt not in options]
        if missing:
            raise ConfigError(name, f"missing option(s): {', '.join(missing)}")
        self.name = name
        self.on_reject = options.get("on_reject", "skip")
        if self.on_reject not in ON_REJECT:
            raise ConfigError(name, f"on_reject must be one of {', '.join(ON_REJECT)}")
        self.stats = {"in": 0, "out": 0, "rejected": 0}
        self.configure(options)

    # hooks for plugins
    def configure(self, options):
        pass

    def open(self, context):
        pass

    def process(self, record):
        raise NotImplementedError

    def flush(self):
        return []

    def close(self):
        pass

    # helpers for plugins
    def reject(self, record, reason):
        raise Reject(record, reason)

    def need(self, record, field):
        """The value of `field`; a record without it (or with None) is rejected."""
        value = record.get(field)
        if value is None:
            self.reject(record, f"missing field {field!r}")
        return value

    # called by the pipeline
    def reset(self):
        self.stats = {"in": 0, "out": 0, "rejected": 0}

    def handle(self, record, dead):
        index = self.stats["in"]
        self.stats["in"] += 1
        try:
            out = self.process(record)
        except Reject as rej:
            self.stats["rejected"] += 1
            if self.on_reject == "fail":
                raise StageError(self.name, index, rej.reason) from None
            dead.append({"stage": self.name, "index": index, "record": record, "reason": rej.reason})
            return []
        except StageError:
            raise
        except Exception as err:
            raise StageError(self.name, index, err) from err
        return self._checked(out, index)

    def run_flush(self):
        try:
            out = self.flush()
        except StageError:
            raise
        except Exception as err:
            raise StageError(self.name, None, err) from err
        return self._checked(out, None)

    def _checked(self, out, index):
        if not isinstance(out, list) or not all(isinstance(r, dict) for r in out):
            raise StageError(self.name, index, "must return a list of dict records")
        self.stats["out"] += len(out)
        return out
