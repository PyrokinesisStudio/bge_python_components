bl_info = {
    "name": "BGE Python Components",
    "author": "agoose77",
    "version": (0, 1),
    "blender": (2, 76, 0),
    "description": "Provides emulation of native UI for BGE Python components",
    "warning": "",
    "wiki_url": "",
    "category": "Game Engine",
    }

from bpy.types import Panel, Object, Operator, PropertyGroup
from bpy.props import StringProperty, CollectionProperty, EnumProperty
from bpy.utils import register_module, unregister_module, register_class

import bpy
import sys
import types

from abc import ABC, abstractmethod
from mathutils import Vector
from contextlib import contextmanager
from os import path
from logging import getLogger, basicConfig, INFO

from .common import load_component_class, group_component_args, COMPONENT_ARG_FORMAT
from .component_base import KX_PythonComponent
from .unions import GameObjectMixin, make_generic_property


MAINLOOP_FILE_NAME = "mainloop.py"
REQUIRED_FILE_NAMES = "component_base.py", "common.py", "component_system.py", "components.py", MAINLOOP_FILE_NAME

ADDON_DIR = path.dirname(__file__)
basicConfig(level=INFO)
logger = getLogger(__name__)


@contextmanager
def guard_modules():
    modules = set(sys.modules)
    yield
    for mod_name in set(sys.modules) - modules:
        del sys.modules[mod_name]


def install_fake_bge_module():
    # Create BGE module
    bge = sys.modules['bge'] = types.ModuleType("bge")
    bge.__component__ = True

    bge.types = sys.modules['bge.types'] = types.ModuleType("bge.types")
    bge.types.KX_PythonComponent = KX_PythonComponent


def initialise_property_group_member(group, value):
    if isinstance(value, (list, set, tuple)):
        prop_name = 'enum'
        group.enum_items = tuple((x, x, x) for x in value)
        value = next(iter(value))

    else:
        if isinstance(value, str):
            prop_name = 'string'

        elif isinstance(value, float):
            prop_name = 'float'

        elif isinstance(value, bool):
            prop_name = 'boolean'

        elif isinstance(value, int):
            prop_name = 'integer'

        elif isinstance(value, Vector):
            assert 1 < len(value) < 5
            prop_name = "vector{}".format(len(value))

        else:
            raise ValueError(value)

    setattr(group, prop_name, value)


def add_game_and_component_properties(obj, prop_name, default_value):
    """Create game property and component property group, and associate the two

    :param obj: object
    :param prop_name: name of property to add
    :param default_value: default parameter value
    """
    # Create game property
    bpy.ops.object.game_property_new(type='STRING', name=prop_name)

    # Create UI property
    component_property = obj.component_properties.add()
    component_property.name = prop_name
    component_property.object_property_name = "component_properties"

    initialise_property_group_member(component_property, default_value)


class LOGIC_OT_add_component(Operator):
    """Add component to object"""
    bl_idname = "logic.component_add"
    bl_label = "Add Game Component"

    NO_IMPORT_PATH = "<NO PATH>"
    import_path = StringProperty(default=NO_IMPORT_PATH)

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        obj = context.active_object

        import_path = self.import_path
        if import_path == self.NO_IMPORT_PATH:
            import_path = obj.component_import_path

        # Fake import of BGE module
        with guard_modules():
            install_fake_bge_module()

            try:
                component_cls = load_component_class(import_path)

            except Exception as err:
                self.report({'ERROR'}, "Unable to import module {!r}: {}".format(import_path, err))
                logger.exception("Unable to import module {!r}".format(import_path))
                return {'CANCELLED'}

        # Load args
        try:
            args = component_cls.args

        except AttributeError:
            args = {}

        properties = obj.game.properties
        component_data = set(group_component_args(properties)) # Values here are game property objects

        if import_path in component_data:
            self.report({'INFO'}, "{!r} component already loaded".format(import_path))
            logger.info("{!r} component already loaded".format(import_path))
            return {'CANCELLED'}

        for name, default_value in args.items():
            prop_name = COMPONENT_ARG_FORMAT.format(import_path=import_path, class_name=name)
            add_game_and_component_properties(obj, prop_name, default_value)

        logger.info("{!r} component loaded".format(import_path))
        return {'FINISHED'}


class LOGIC_OT_remove_component(Operator):
    """Remove component from object"""
    bl_idname = "logic.component_remove"
    bl_label = "Remove Game Component"

    import_path = StringProperty()

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        obj = context.active_object
        properties = obj.game.properties
        import_path = self.import_path

        if not import_path:
            self.report({'ERROR'}, "Import path is required to remove component")
            logger.error("Import path is required to remove component")
            return {'CANCELLED'}

        component_data = group_component_args(properties) # Values here are game property objects

        try:
            component_args = component_data[import_path]

        except KeyError:
            self.report({'ERROR'}, "Import path is not present in current components")
            logger.error("Import path {!r} is not present in current components".format(import_path))
            return {'CANCELLED'}

        for game_property in component_args.values():
            game_property_name = game_property.name

            index = properties.find(game_property_name)
            if index != -1:
                bpy.ops.object.game_property_remove(index=index)

            c_index = obj.component_properties.find(game_property_name)
            if c_index != -1:
                obj.component_properties.remove(c_index)

        logger.info("{!r} component removed".format(import_path))
        return {'FINISHED'}


class LOGIC_OT_reload_component(Operator):
    """Reload component from disk"""
    bl_idname = "logic.component_reload"
    bl_label = "Reload Game Component"

    import_path = StringProperty()

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        import_path = self.import_path

        if not import_path:
            self.report({'ERROR'}, "Import path is required to reload component")
            logger.info("Import path is required to reload component")
            return {'CANCELLED'}

        # Remove component
        bpy.ops.logic.component_remove(import_path=import_path)

        # Add component
        bpy.ops.logic.component_add(import_path=import_path)

        self.report({'INFO'}, "{!r} component reloaded".format(import_path))
        logger.info("{!r} component reloaded".format(import_path))
        return {'FINISHED'}


class LOGIC_PT_draw_components(Panel):
    bl_space_type = 'LOGIC_EDITOR'
    bl_region_type = 'UI'
    bl_label = 'Components'

    @classmethod
    def poll(cls, context):
        ob = context.active_object
        return ob and ob.name

    def draw(self, context):
        layout = self.layout

        ob = context.active_object
        game = ob.game

        row = layout.row()
        row.prop(ob, "component_import_path", text="")
        row.operator("logic.component_add", text="Add Component")

        components_data = group_component_args(game.properties)

        for import_path, component_args in components_data.items():
            box = layout.box()

            row = box.row()
            row.label(text=import_path)

            row.operator("logic.component_reload", text="", icon='RECOVER_LAST', emboss=False).import_path = import_path
            row.operator("logic.component_remove", text="", icon='X', emboss=False).import_path = import_path

            for name, prop in component_args.items():
                row = box.row()
                display_prop_name = name.replace('_', ' ').title()
                row.label(display_prop_name)

                group = ob.component_properties[prop.name]
                group.prop(row.column())


class PersistantHandler(ABC):

    @classmethod
    def tag_class(cls, func):
        func._class = cls
        return func

    @classmethod
    def find_from_tag(cls, funcs):
        for func in funcs:
            if not hasattr(func, "_class"):
                continue

            if func._class is cls:
                return func

        raise ValueError

    @classmethod
    def install(cls, *args, **kwargs):
        instance = cls(*args, **kwargs)

        @bpy.app.handlers.persistent
        @cls.tag_class
        def update(scene):
            instance.update(scene)

        bpy.app.handlers.scene_update_post.append(update)

    @classmethod
    def uninstall(cls):
        handlers = bpy.app.handlers.scene_update_post
        handler = cls.find_from_tag(handlers)
        handlers.remove(handler)

    @abstractmethod
    def update(self, scene):
        pass


class TextBlockMonitor(PersistantHandler):
    """Monitor text blocks to replace missing component scripts"""

    def __init__(self, required_file_names):
        self._required_file_names = required_file_names

    def update(self, scene):
        for file_name in self._required_file_names:
            if file_name not in bpy.data.texts:
                text_block = bpy.data.texts.new(file_name)

                with open(path.join(ADDON_DIR, file_name), 'r') as f:
                    text_block.from_string(f.read())


class ScenePropMonitor(PersistantHandler):
    """Monitor scene __main__ ID property to install component gameloop"""

    def __init__(self, mainloop_file_name):
        self._mainloop_file_name = mainloop_file_name

    def update(self, scene):
        scene['__main__'] = self._mainloop_file_name


# Build GameObjectProperty property group
GameObjectProperty = make_generic_property(GameObjectMixin)


def register():
    register_module(__name__)
    register_class(GameObjectProperty)

    Object.component_import_path = StringProperty()
    Object.component_properties = bpy.props.CollectionProperty(type=GameObjectProperty)

    TextBlockMonitor.install(REQUIRED_FILE_NAMES)
    ScenePropMonitor.install(MAINLOOP_FILE_NAME)


def unregister():
    ScenePropMonitor.uninstall()
    TextBlockMonitor.uninstall()
    del Object.component_import_path
    del Object.component_properties

    unregister_module(__name__)


if __name__ == "__main__":
    register()
