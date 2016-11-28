from bpy.types import PropertyGroup
from bpy.props import StringProperty, IntProperty, FloatProperty, BoolProperty, FloatVectorProperty, CollectionProperty, \
    EnumProperty

import bpy

from collections import OrderedDict, deque
from collections.abc import Sequence
from itertools import chain

from .common import to_json_string, from_json_string


def enum_encode(self, index):
    """Encode enum int as name"""
    return self.enum_items[index][0]


def enum_decode(self, value):
    """Decode enum name as int"""
    for i, entry in enumerate(self.enum_items):
        if entry[0] == value:
            return i
    raise ValueError


# Modifiers to change values pre/post JSON serialisers
modifiers = {'enum': (enum_encode, enum_decode)}


def make_generic_getter(name):
    def getter(self):
        return self.member_get(name)

    return getter


def make_generic_setter(name):
    def setter(self, value):
        self.member_set(name, value)

    return setter


_enum_items_referee = deque(maxlen=256) # Hold onto enum items whilst they are in use. It is unlikely that >256 need to be displayed at the same time.


class GenericPropertyMixin:
    
    private_enum_items = StringProperty(default=to_json_string([]))

    @property
    def enum_items(self):
        items = tuple(tuple(x) for x in from_json_string(self.private_enum_items))
        _enum_items_referee.append(items)
        return items

    @enum_items.setter
    def enum_items(self, value):
        assert isinstance(value, Sequence) # Must be a Sequence
        assert all(isinstance(g, tuple) for g in value) # Sequence of tuples
        assert all(isinstance(x, str) for g in value for x in g) # Sequence of tuples of strings

        self.private_enum_items = to_json_string(value)

    def member_set(self, name, value):
        self[name] = value

    def member_get(self, name):
        return self[name]


class DynamicMixin(GenericPropertyMixin):
    private_generic_type_name = StringProperty()

    def value_set(self, name, value):
        self['value'] = value

    def value_get(self, name):
        return self['value']

    def member_set(self, name, value):
        if name != self.private_generic_type_name and self.private_generic_type_name:
            raise TypeError
        self.private_generic_type_name = name

        self.value_set(name, value)

    def member_get(self, name):
        if name != self.private_generic_type_name and self.private_generic_type_name:
            raise TypeError

        return self.value_get(name)

    def prop(self, layout):
        return layout.prop(self, self.private_generic_type_name, text="")


class GameObjectMixin(DynamicMixin):
    object_property_name = StringProperty()

    @property
    def owner_object(self):
        container_name = self.object_property_name
        assert container_name, \
            "The name of the attribute of the object in which this struct is contained was not provided"

        pointer = self.as_pointer()

        for obj in chain((bpy.context.object,), bpy.data.objects):
            for obj_struct in getattr(obj, container_name):
                if obj_struct.as_pointer() == pointer:
                    return obj
        raise ValueError

    @property
    def game_property(self):
        """Return the game property of the owner object with the same name"""
        assert self.name, \
            "The name of the struct equating to the owner object's game property was not given"
        return self.owner_object.game.properties[self.name]

    def serialise(self, name, value):
        """Serialise one of the Union values into a JSON string"""
        try:
            encode, decode = modifiers[name]
        except KeyError:
            pass
        else:
            value = encode(self, value)

        return to_json_string(value)

    def deserialise(self, name, value):
        """Deserialise one of the Union values from a JSON string"""
        value = from_json_string(value)

        try:
            encode, decode = modifiers[name]
        except KeyError:
            pass
        else:
            value = decode(self, value)

        return value

    def value_set(self, name, value):
        """Callback when the selected generic type is written to"""
        serialised_value = self.serialise(name, value)
        self.game_property.value = serialised_value

    def value_get(self, name):
        """Callback when the selected generic type is read from"""
        serialised_value = self.game_property.value
        return self.deserialise(name, serialised_value)


def get_enum_items(self, ctx):
    return self.enum_items


factories = OrderedDict((
    ('vector2', (FloatVectorProperty, {'size': 2, 'subtype': 'XYZ'})),
    ('vector3', (FloatVectorProperty, {'size': 3, 'subtype': 'XYZ'})),
    ('vector4', (FloatVectorProperty, {'size': 4, 'subtype': 'XYZ'})),
    ('integer', (IntProperty, {})),
    ('boolean', (BoolProperty, {})),
    ('float', (FloatProperty, {})),
    ('string', (StringProperty, {})),
    ('enum', (EnumProperty, {'items': get_enum_items})),
))


def make_generic_property(base_cls):
    cls_dict = {}

    for name, (factory, params) in factories.items():
        cls_dict[name] = factory(get=make_generic_getter(name), set=make_generic_setter(name), **params)

    return type(base_cls.__name__ + 'Group', (base_cls, PropertyGroup), cls_dict)
