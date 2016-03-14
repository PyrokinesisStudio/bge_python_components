def load_component_class(import_path):
    module_path, class_name = import_path.rsplit('.', 1)
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
