from collections import namedtuple


ComponentProperty = namedtuple("ComponentProperty", "import_path arg_name")


def load_component_class(import_path):
    try:
        module_path, class_name = import_path.rsplit('.', 1)
    except ValueError:
        raise ValueError("Invalid import path {!r}: too few '.' separated names (expected two or more)".format(import_path))

    module = __import__(module_path, fromlist=[class_name])
    print(dir(module), module)
    cls = getattr(module, class_name)
    return cls


COMPONENT_ARG_PREFIX = "$"
COMPONENT_ARG_SEP = ":"
COMPONENT_ARG_FORMAT = COMPONENT_ARG_PREFIX + "{import_path}" + COMPONENT_ARG_SEP + "{class_name}"


def parse_component_arg_name(name):
    start_import_path = name.find(COMPONENT_ARG_PREFIX) + len(COMPONENT_ARG_PREFIX)
    end_import_path = name.find(COMPONENT_ARG_SEP)
    start_arg_name = end_import_path + len(COMPONENT_ARG_SEP)

    if start_import_path == -1 or end_import_path == -1:
        raise ValueError

    return ComponentProperty(name[start_import_path:end_import_path], name[start_arg_name:])


def parse_component_args(properties):
    components = {}

    for name, value in properties.items():
        try:
            data = parse_component_arg_name(name)
        except ValueError:
            continue

        try:
            component_data = components[data.import_path]
        except KeyError:
            component_data = components[data.import_path] = {}

        component_data[data.arg_name] = value

    return components