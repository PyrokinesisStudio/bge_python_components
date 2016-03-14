from bge import logic, types
from common import load_component_class, ARG_PROPERTY_NAME, COMPONENTS_NAME, COMPONENT_PATHS_NAME, path_to_list


# Create fake base class
from component_base import KX_PythonComponent
types.KX_PythonComponent = KX_PythonComponent


def any_positive(sensors):
    for sens in sensors:
        if sens.positive:
            return True

    return False


def create_args_dict(component_cls, obj, import_path):
    try:
        arg_defaults = component_cls.args

    except AttributeError:
        return {}

    args = {}
    for name, default_value in arg_defaults.items():
        prop_name = ARG_PROPERTY_NAME.format(import_path=import_path, class_name=name)
        args[name] = obj.get(prop_name, default_value)

    return args


def init_components(obj, component_paths):
    components = []

    for import_path in component_paths:
        cls = load_component_class(import_path)

        args = create_args_dict(cls, obj, import_path)

        component = cls(obj)
        component.start(args)

        components.append(component)

    return components


def update_components(components):
    for component in components:
        component.update()


def update_from_controller(cont):
    if not any_positive(cont.sensors):
        return

    own = cont.owner
    scene = own.scene

    update_scene(scene)


def update_scene(scene):
    for obj in scene.objects:
        if COMPONENT_PATHS_NAME not in obj:
            continue

        component_paths_string = obj[COMPONENT_PATHS_NAME]
        component_paths = path_to_list(component_paths_string)

        if COMPONENTS_NAME not in obj:
            obj[COMPONENTS_NAME] = init_components(obj, component_paths)

        components = obj[COMPONENTS_NAME]
        update_components(components)
