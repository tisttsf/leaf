"""用户视图函数"""

from typing import List

from flask import request
from flask import send_file
from flask import Response
from bson import ObjectId

from . import rbac

from ...core import tools
from ...api import validator
from ...api import wrapper

from ...rbac import error
from ...rbac.model import User
from ...rbac.model import UserIndex
from ...rbac import settings as _rbac_settings
from ...rbac.functions import auth as authfuncs
from ...rbac.functions import user as functions


@rbac.route("/users", methods=["GET"])
@wrapper.require("leaf.views.rbac.user.get")
@wrapper.wrap("users")
def get_batch_users() -> List[User]:
    """批量获取用户信息 - 暂时只能根据ID正向排序"""
    previous: ObjectId = request.args.get(
        "previous", default='0' * 24, type=str)
    previous = validator.objectid(previous)
    count: int = request.args.get("count", default=0, type=int)
    # pylint: disable=no-member
    return User.objects(id__gt=previous).limit(count)


@rbac.route("/users/<string:userid>", methods=["GET"])
@wrapper.require("leaf.views.rbac.user.get")
@wrapper.wrap("user")
def get_user_byid(userid: str) -> User:
    """根据用户 ID 查询用户"""
    userid = validator.objectid(userid)
    return functions.Retrieve.byid(userid)


@rbac.route("/users/<string:indexid>/<string:index>", methods=["GET"])
@wrapper.require("leaf.views.rbac.user.get")
@wrapper.wrap("users")
def get_user_byindex(indexid: str, index: str) -> User:
    """根据用户 Index 查询用户"""
    users: List[User] = functions.Retrieve.byindex(indexid, index)
    return users


@rbac.route("/users/<string:userid>/informations", methods=["PUT"])
@wrapper.require("leaf.views.rbac.user.update", checkuser=True)
@wrapper.wrap("user")
def update_user_informations(userid: str) -> User:
    """更新用户 informations 信息"""
    userid = validator.operator(userid)
    user: User = functions.Retrieve.byid(userid)
    informations: dict = request.form.to_dict()
    user.informations = informations
    return user.save()


@rbac.route("/users", methods=["POST"])
@wrapper.require("leaf.views.rbac.user.create")
@wrapper.wrap("user")
def create_user() -> User:
    """
    创建一个用户的接口调用顺序如下:
        1. 首先调用创建用户接口 - User(**info...)
        2. 调用为用户设置密码接口 - auth.Create.withuserid
        3. 为用户设置文档ID索引 - user.Update.inituser
    这里密码应该通过 post 参数传入
    """
    password: str = request.form.get("password", type=str, default='')
    user: User = User()
    user.save()
    # pylint: disable=no-member
    authfuncs.Create.withuserid(user.id, password)
    return functions.Update.inituser(user.id)


@rbac.route("/users/<string:userid>/status", methods=["PUT"])
@wrapper.require("leaf.views.rbac.user.update")
@wrapper.wrap("user")
def update_user_status(userid: str) -> User:
    """更新一个用户的状态"""
    userid = validator.objectid(userid)
    status: bool = request.form.get("status", default=True, type=bool)
    user: User = functions.Retrieve.byid(userid)
    user.disabled = not status
    return user.save()


@rbac.route("/users/<string:userid>/groups/<string:groupid>", methods=["POST"])
@wrapper.require("leaf.views.rbac.user.update", checkuser=True)
@wrapper.wrap("user")
def add_user_to_group(userid: str, groupid: str) -> User:
    """将用户添加至用户组"""
    groupid = validator.objectid(groupid)
    userid = validator.operator(userid)
    return functions.Create.group(userid, groupid)


@rbac.route("/users/<string:userid>/indexs", methods=["POST"])
@wrapper.require("leaf.views.rbac.user.update", checkuser=True)
@wrapper.wrap("indexs")
def update_user_index(userid: str) -> List[UserIndex]:
    """
    为指定用户增加一个索引信息
    请确保给定的索引方式在 rbac.settings.User.Index 中存在
    """
    userid = validator.operator(userid)
    indexs = dict(_rbac_settings.User.Indexs.values())

    typeid = request.form.get("typeid", type=str)
    value = request.form.get("value", type=str)
    extension = request.form.get("extension", type=str, default="{}")
    extension = tools.web.JSONparser(extension)
    if not typeid in indexs.keys():
        raise error.UndefinedUserIndex(typeid)

    description = indexs.get(typeid)
    index = UserIndex(typeid, value, description, extension)
    return functions.Create.index(userid, index)


@rbac.route("/users/<string:userid>/indexs/<string:typeid>", methods=["DELETE"])
@wrapper.require("leaf.views.rbac.user.update", checkuser=True)
@wrapper.wrap("indexs")
def delete_user_index(userid: str, typeid: str) -> List[UserIndex]:
    """删除用户的一种指定索引"""
    userid = validator.operator(userid)
    return functions.Delete.index(userid, typeid)


@rbac.route("/users/<string:userid>", methods=["DELETE"])
@wrapper.require("leaf.views.rbac.user.delete", checkuser=True)
@wrapper.wrap("status")
def delete_user(userid: str) -> bool:
    """删除某一个用户"""
    userid = validator.operator(userid)
    user: User = functions.Retrieve.byid(userid)
    user.delete()
    return True


@rbac.route("/users/<string:userid>/groups/<string:groupid>", methods=["DELETE"])
@wrapper.require("leaf.views.rbac.user.update", checkuser=True)
@wrapper.wrap("status")
def remove_user_from_group(userid: str, groupid: str) -> bool:
    """将用户从组中移除"""
    groupid = validator.objectid(groupid)
    userid = validator.operator(userid)
    functions.Delete.group(userid, groupid)
    return True


@rbac.route("/users/indexs", methods=["GET"])
@wrapper.wrap("indexs")
def get_all_indexs() -> dict:
    """获取所有的索引类型信息"""
    return _rbac_settings.User.Indexs


@rbac.route("/users/avatar/<string:userid>", methods=["POST"])
@wrapper.require("leaf.views.rbac.user.update", checkuser=True)
@wrapper.wrap("size")
def update_user_avatar(userid: str) -> int:
    """更新用户头像"""
    userid = validator.objectid(userid)
    user = functions.Retrieve.byid(userid)
    avatar = request.files.get("avatar", None)
    if user.avatar.gridout and avatar:
        user.avatar.replace(avatar)
        user.save()
        return user.avatar.length
    return 0


@rbac.route("/users/avatar/<string:userid>", methods=["DELETE"])
@wrapper.require("leaf.views.rbac.user.update", checkuser=True)
@wrapper.wrap("status")
def delete_user_avatar(userid: str) -> bool:
    """删除用户头像"""
    userid = validator.objectid(userid)
    user = functions.Retrieve.byid(userid)
    if user.avatar.size:
        user.avatar.delete()
        user.save()
        return True
    return False


@rbac.route("/users/avatar/<string:userid>", methods=["GET"])
def get_user_avatar(userid: str) -> bytes:
    """获取用户头像"""
    userid = validator.objectid(userid)
    user = functions.Retrieve.byid(userid)
    is_thumbnail = bool(request.args.get("thumbnail", type=int, default=0))

    # 检查用户是否有头像
    if not user.avatar.size:
        return Response(status=404)

    # 判断请求的是否为缩略图
    if is_thumbnail:
        handler = user.avatar.thumbnail
    else:
        handler = user.avatar.get()

    # 检查是否缓存过
    last_requested = request.headers.get("If-Modified-Since")
    last_modified = handler.upload_date
    if last_requested == last_modified:
        return Response(status=304)

    return send_file(handler, last_modified=last_modified,
                     mimetype="image/" + user.avatar.format.lower())
