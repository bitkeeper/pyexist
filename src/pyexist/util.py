
class safe(str):
    pass

def escape(arg):
    if isinstance(arg, safe):
        return arg
    elif isinstance(arg, int):
        return str(arg)
    elif isinstance(arg, str) or isinstance(arg, unicode):
        return arg.encode('ascii', 'ignore').replace(r"'", r"''")
    elif hasattr(arg, '__iter__'):
        items = [("'" + escape(i) + "'") for i in arg]
        return ', '.join(items)
    else:
        return str(arg).replace(r"'", r"''")

def replacetags(string, **kwargs):
    for key, value in kwargs.iteritems():
        string = string.replace('%{' + key + '}', escape(value))
    return string
