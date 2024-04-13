from bpy.types import Context, Bone
from mathutils import *


def deselect_all_bones_from_active(context: Context) -> None:
    if context.active_object is None:
        return
    if context.active_object.type != 'ARMATURE':
        return
    if context.mode == 'POSE':
        armature_bones: dict[str, Bone] = context.active_object.data.bones
        for bone in context.selected_pose_bones_from_active_object:
            armature_bones[bone.name].select = False
    elif context.mode == 'EDIT_ARMATURE':
        for bone in context.selected_bones:
            bone.select = False


def select_all_bones_from_active(context: Context) -> None:
    if context.active_object is None:
        return
    if context.active_object.type != 'ARMATURE':
        return
    armature_bones: list[Bone] = context.active_object.data.bones
    for bone in armature_bones:
        bone.select = True


def get_bone_co_pose_space(armature, bone_name: str, tip_or_head: str = 'HEAD') -> Matrix:
    """Expects an active Armature object, and if run as main an empty object called "Empty" """
    bone: Bone = armature.data.bones[bone_name]

    Mtip = Matrix.Translation(bone.tail)
    Mhead = Matrix.Translation(bone.head)

    if tip_or_head.lower() == "tip":
        dest = Mtip
    elif tip_or_head.lower() == "head":
        dest = Mhead

    if bone.parent:
        Mptip = Matrix.Translation(bone.parent.tail - bone.parent.head)
        #head and orientation of parent bone
        temp: Matrix =  bone.parent.matrix_local
        Mw   =  temp.copy()
        #grandfather orientation
        Mw *= bone.parent.matrix.to_4x4().inverted()
        #tip of parent bone
        Mw *= Mptip
        #back to orientation of parent bone
        Mw *= bone.parent.matrix.to_4x4()
        #tip of bone
        Mw *= dest
        #orientation of bone
        Mw *= bone.matrix.to_4x4()
    else:
        temp: Matrix =  bone.matrix_local
        Mw   =  temp.copy()
        Mw *= bone.matrix.to_4x4().inverted()
        Mw *= dest
        Mw *= bone.matrix.to_4x4()

    return Mw
