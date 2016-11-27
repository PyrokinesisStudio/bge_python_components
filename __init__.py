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



from bpy.types import Panel, Object, Operator
from bpy.props import StringProperty, IntProperty, FloatProperty, BoolProperty
from bpy.utils import register_module, unregister_module

import bpy
import sys
import types

from contextlib import contextmanager
from os import path
from weakref import ref
from logging import getLogger

from .component_base import KX_PythonComponent
from .common import load_component_class, parse_component_args, COMPONENT_ARG_FORMAT


MAINLOOP_FILE_NAME = "mainloop.py"
REQUIRED_FILE_NAMES = "component_base.py", "common.py", "component_system.py", "components.py", MAINLOOP_FILE_NAME


ADDON_DIR = path.dirname(__file__)
logger = getLogger(__name__)


@contextmanager
def guard_modules():
    modules = set(sys.modules)
    yield
    for mod_name in set(sys.modules) - modules:
        del sys.modules[mod_name]


def prop_type_from_value(value):
    type_map = {str: 'STRING', int: 'INT', float: 'FLOAT', bool: 'BOOL'}
    return type_map[type(value)]


def get_prefixed_properties(properties, prefix):
    return [p for p in properties if p.name.startswith(prefix)]


def component_is_already_loaded(properties, import_path):
    pass


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

        # Fake import
        with guard_modules():
            # Create BGE module
            bge = sys.modules['bge'] = types.ModuleType("bge")
            bge.types = sys.modules['bge.types'] = types.ModuleType("bge.types")
            bge.types.KX_PythonComponent = KX_PythonComponent

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
        component_data = set(parse_component_args(properties)) # Values here are game property objectss

        if import_path in component_data: # TODO
            self.report({'INFO'}, "{!r} component already loaded".format(import_path))
            logger.info("{!r} component already loaded".format(import_path))
            return {'CANCELLED'}

        for name, default_value in args.items():
            prop_name = COMPONENT_ARG_FORMAT.format(import_path=import_path, class_name=name)
            prop_type = prop_type_from_value(default_value)
            bpy.ops.object.game_property_new(type=prop_type, name=prop_name)

            prop = properties[prop_name]
            prop.value = default_value

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

        component_data = parse_component_args(properties) # Values here are game property objects
        for import_path, component_args in component_data.items():
            for game_property in component_args.values():
                index = properties.find(game_property.name)
                if index == -1:
                    continue

                bpy.ops.object.game_property_remove(index=index)

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


class LOGIC_PT_components(Panel):
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

        components_data = parse_component_args(game.properties)

        for import_path, component_args in components_data.items():
            box = layout.box()

            row = box.row()
            row.label(text=import_path)

            row.operator("logic.component_reload", text="", icon='RECOVER_LAST', emboss=False).import_path = import_path
            row.operator("logic.component_remove", text="", icon='X', emboss=False).import_path = import_path

            for name, prop in component_args.items():
                row = box.row()
                row.label(name)
                row.prop(prop, "value", text="")


class PersistantHandler:

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


class TextBlockMonitor(PersistantHandler):

    def __init__(self, required_file_names):
        self._required_file_names = required_file_names

    def update(self, scene):
        for file_name in self._required_file_names:
            if file_name not in bpy.data.texts:
                text_block = bpy.data.texts.new(file_name)

                with open(path.join(ADDON_DIR, file_name), 'r') as f:
                    text_block.from_string(f.read())


class ScenePropMonitor(PersistantHandler):

    def __init__(self, mainloop_file_name):
        self._mainloop_file_name = mainloop_file_name

    def update(self, scene):
        scene['__main__'] = self._mainloop_file_name


def register():
    register_module(__name__)

    Object.component_import_path = StringProperty()
    TextBlockMonitor.install(REQUIRED_FILE_NAMES)
    ScenePropMonitor.install(MAINLOOP_FILE_NAME)


def unregister():
    ScenePropMonitor.uninstall()
    TextBlockMonitor.uninstall()
    del Object.component_import_path

    unregister_module(__name__)


if __name__ == "__main__":
    register()
