from collections import namedtuple
from json import JSONEncoder, JSONDecoder, dumps, loads
from mathutils import Vector

component_names = 'xyzw'
component_to_index = {c: i for i, c in enumerate(component_names)}


class VectorEncoder(JSONEncoder):

    def default(self, obj):
        if isinstance(obj, Vector):
            return {'vector': {k: v for k, v in zip(component_names, obj)}}

        return super().default(obj)


class VectorDecoder(JSONDecoder):

    def __init__(self, *args, **kwargs):
        super().__init__(object_hook=self.object_hook, *args, **kwargs)

    def object_hook(self, obj):
        if 'vector' in obj:
            vect = obj['vector']
            values = list(vect.items())
            values.sort(key=lambda a: component_to_index[a[0]])
            names, components = zip(*values)
            return Vector(components)

        return obj


def to_json_string(value):
    return dumps(value, cls=VectorEncoder)


def from_json_string(json):
    return loads(json, cls=VectorDecoder)


ComponentProperty = namedtuple("ComponentProperty", "import_path arg_name")


def load_component_class(import_path):
    try:
        module_path, class_name = import_path.rsplit('.', 1)
    except ValueError:
        raise ValueError("Invalid import path {!r}: too few '.' separated names (expected two or more)"
                         .format(import_path))

    module = __import__(module_path, fromlist=[class_name])
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


def group_component_args(properties):
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