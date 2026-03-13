def check_type(obj, target_class):
    if not isinstance(obj, target_class):
        msg = f"{obj} is not {target_class}"
        return TypeError(msg)


class NoDbusConnectionError(Exception):
    def __init__(self):
        msg = "Ther is no dbus connection"
        super().__init__(msg)

