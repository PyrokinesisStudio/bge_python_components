from bge import logic, types
from common import load_component_class, group_component_args, from_json_string


# Create fake base class
from component_base import KX_PythonComponent
types.KX_PythonComponent = KX_PythonComponent


COMPONENTS_NAME = "components"


def any_positive(sensors):
    for sens in sensors:
        if sens.positive:
            return True

    return False


def create_args_dict(component_cls, raw_component_args):
    try:
        base_args = component_cls.args.copy()

    except AttributeError:
        base_args = {}

    component_args = {k: from_json_string(v) for k, v in raw_component_args.items()}
    base_args.update(component_args)
    return base_args


def init_components(obj):
    components = []

    # Load properties from object
    prop_dict = {k: obj[k] for k in obj.getPropertyNames()}

    component_data = group_component_args(prop_dict)
    for import_path, raw_component_args in component_data.items():
        cls = load_component_class(import_path)

        args = create_args_dict(cls, raw_component_args)

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
        if COMPONENTS_NAME not in obj:
            obj[COMPONENTS_NAME] = init_components(obj)

        components = obj[COMPONENTS_NAME]
        update_components(components)
