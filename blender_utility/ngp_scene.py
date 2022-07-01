from types import UnionType

import bpy
from instant_ngp_tools.blender_utility.logging_utility import log_report
from instant_ngp_tools.blender_utility.object_utility import (
    add_collection,
    add_cube,
    add_empty,
    get_collection,
    get_object
)

MAIN_COLLECTION_ID = "Instant-NGP Tools"
GLOBAL_TRANSFORM_ID = "GLOBAL_TRANSFORM"
AABB_BOX_ID = "AABB_BOX"

# TODO: Come up with a way to present NGP coords instead of Blender/NeRF coords
AABB_SIZE_ID = "aabb_size"
AABB_SIZE_DEFAULT = 16 / 0.33
AABB_MIN_ID = "aabb_min"
AABB_MIN_DEFAULT = (-AABB_SIZE_DEFAULT / 2, -AABB_SIZE_DEFAULT / 2, -AABB_SIZE_DEFAULT / 2)
AABB_MAX_ID = "aabb_max"
AABB_MAX_DEFAULT = (AABB_SIZE_DEFAULT / 2, AABB_SIZE_DEFAULT / 2, AABB_SIZE_DEFAULT / 2)

class NGPScene:
    @classmethod
    def main_collection(cls):
        collection = get_collection(MAIN_COLLECTION_ID)
        return collection
    
    @classmethod
    def create_main_collection(cls):
        collection = cls.main_collection()
        if collection is None:
            collection = add_collection(MAIN_COLLECTION_ID)
        return collection

    @classmethod
    def global_transform(cls):
        return get_object(GLOBAL_TRANSFORM_ID)
    
    @classmethod
    def create_global_transform(cls):
        collection = cls.main_collection()
        obj = cls.global_transform()
        if obj is None:
            obj = add_empty(GLOBAL_TRANSFORM_ID, collection)
        if not obj.name in collection.objects:
            cls.main_collection().objects.link(obj)
        return obj
    
    @classmethod
    def create_aabb_box(cls):
        collection = cls.main_collection()
        obj = cls.aabb_box()
        if obj is None:
            obj = add_cube(AABB_BOX_ID, collection)
            obj.display_type = 'BOUNDS'
            
            # Set up custom AABB min prop
            obj[AABB_MIN_ID] = AABB_MIN_DEFAULT
            prop = obj.id_properties_ui(AABB_MIN_ID)
            prop.update(precision=5)

            # Set up custom AABB max prop
            obj[AABB_MAX_ID] = AABB_MAX_DEFAULT
            prop = obj.id_properties_ui(AABB_MAX_ID)
            prop.update(precision=5)

            # Helper method for adding min/max vars to a driver
            def add_min_max_vars(driver: bpy.types.Driver, axis: int):
                axis_name = ["x", "y", "z"][axis]
                
                vmin = driver.variables.new()
                vmin.name = f"{axis_name}_min"
                vmin.targets[0].id = obj
                vmin.targets[0].data_path = f"[\"{AABB_MIN_ID}\"][{axis}]"

                vmax = driver.variables.new()
                vmax.name = f"{axis_name}_max"
                vmax.targets[0].id = obj
                vmax.targets[0].data_path = f"[\"{AABB_MAX_ID}\"][{axis}]"

            # Set up drivers for location
            [px, py, pz] = [fc.driver for fc in obj.driver_add('location', -1)]

            add_min_max_vars(px, 0)
            px.expression = "0.5 * (x_min + x_max)"

            add_min_max_vars(py, 1)
            py.expression = "0.5 * (y_min + y_max)"

            add_min_max_vars(pz, 2)
            pz.expression = "0.5 * (z_min + z_max)"
            
            # Set up drivers for scale
            [sx, sy, sz] = [fc.driver for fc in obj.driver_add('scale', -1)]

            add_min_max_vars(sx, 0)
            sx.expression = "x_max - x_min"

            add_min_max_vars(sy, 1)
            sy.expression = "y_max - y_min"

            add_min_max_vars(sz, 2)
            sz.expression = "z_max - z_min"
        
        if not obj.name in collection.objects:
            collection.objects.link(obj)
        
        return obj

    @classmethod
    def aabb_box(cls):
        return get_object(AABB_BOX_ID)

    @classmethod
    def is_setup(cls):
        return (
            cls.main_collection() is not None
            and cls.aabb_box() is not None
            and cls.global_transform() is not None
        )
    
    @classmethod
    def get_aabb_min(cls):
        return cls.aabb_box()[AABB_MIN_ID]
    
    @classmethod
    def set_aabb_min(cls, value):
        aabb_max = cls.get_aabb_max()
        safe_max = [
            min(value[0], aabb_max[0]),
            min(value[1], aabb_max[1]),
            min(value[2], aabb_max[2]),
        ]
        cls.aabb_box()[AABB_MIN_ID] = safe_max
        cls.update_aabb_box_drivers()

    @classmethod
    def get_aabb_max(cls):
        return cls.aabb_box()[AABB_MAX_ID]
    
    @classmethod
    def set_aabb_max(cls, value):
        aabb_min = cls.get_aabb_min()
        safe_max = [
            max(value[0], aabb_min[0]),
            max(value[1], aabb_min[1]),
            max(value[2], aabb_min[2]),
        ]
        cls.aabb_box()[AABB_MAX_ID] = safe_max
        cls.update_aabb_box_drivers()
    
    @classmethod
    def update_aabb_box_drivers(cls):
        obj = cls.aabb_box()
        # dirty hack - re-evaluates drivers (thank you https://blenderartists.org/t/driver-update-dependencies-via-script/1126347)
        for driver in obj.animation_data.drivers:
            orig_expr = driver.driver.expression
            # add a space to the expression, then remove it
            driver.driver.expression = f"{orig_expr} "
            driver.driver.expression = orig_expr
