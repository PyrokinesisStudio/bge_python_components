def load_component_class(import_path):
    try:
        module_path, class_name = import_path.rsplit('.', 1)
    except ValueError:
        raise ValueError("Invalid import path {!r}: too few '.' separated names (expected two or more)".format(import_path))

    module = __import__(module_path, fromlist=[class_name])
    cls = getattr(module, class_name)
    return cls


def path_to_list(path):
    return [p for p in path.strip().split(',') if p]


def list_to_path(sequence):
    return ",".join(sequence)


COMPONENT_PATHS_NAME = "_component_paths"
COMPONENTS_NAME = "components"
ARG_PROPERTY_NAME = "{import_path}.{class_name}"
