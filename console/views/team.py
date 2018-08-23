# -*- coding: utf8 -*-
import logging

from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Q
from rest_framework.response import Response

from backends.services.exceptions import *
from backends.services.resultservice import *
from console.services.enterprise_services import enterprise_services
from console.services.team_services import team_services
from console.services.user_services import user_services
from console.services.perm_services import perm_services
from console.services.region_services import region_services
from console.views.base import JWTAuthApiView
from www.models import Tenants
from console.repositories.plugin import config_group_repo, config_item_repo
from www.perms import PermActions, get_highest_identity
from www.utils.crypt import make_uuid
from www.utils.return_message import general_message, error_message
from console.services.plugin import plugin_service, plugin_version_service
from console.repositories.perm_repo import role_repo

logger = logging.getLogger("default")


class UserFuzSerView(JWTAuthApiView):
    def get(self, request, *args, **kwargs):
        """
        模糊查询用户
        ---
        parameters:
            - name: query_key
              description: 模糊用户名
              required: true
              type: string
              paramType: query
        """
        try:
            query_key = request.GET.get("query_key", None)
            if query_key:
                q_obj = Q(nick_name__icontains=query_key) | Q(email__icontains=query_key)
                users = user_services.get_user_by_filter(args=(q_obj,))
                user_list = [
                    {
                        "nick_name": user_info.nick_name,
                        "email": user_info.email,
                        "user_id": user_info.user_id
                    }
                    for user_info in users
                ]
                result = general_message(200, "query user success", "查询用户成功", list=user_list)
                return Response(result, status=200)
            else:
                result = general_message(200, "query user success", "你没有查询任何用户")
                return Response(result, status=200)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=500)


class TeamUserDetaislView(JWTAuthApiView):

    def get_highest_identity(self, identitys):
        identity_map = {"access": 1, "viewer": 2, "developer": 3, "admin": 4, "owner": 5}
        final_identity = identitys[0]
        identity_num = -1
        for i in identitys:
            num = identity_map.get(final_identity)
            if num > identity_num:
                final_identity = i
                identity_num = num
        return final_identity

    def get(self, request, team_name, user_name, *args, **kwargs):
        """
        用户详情
        ---
        parameters:
            - name: team_name
              description: 团队名
              required: true
              type: string
              paramType: path
            - name: user_name
              description: 用户名
              required: true
              type: string
              paramType: path
        """
        try:
            # u, perms = user_services.get_user_detail(tenant_name=team_name, nick_name=user_name)
            team = team_services.get_tenant_by_tenant_name(team_name)
            is_user_enter_amdin = user_services.is_user_admin_in_current_enterprise(self.user, team.enterprise_id)
            perms = team_services.get_user_perm_identitys_in_permtenant(self.user.user_id, team_name)
            role_list = team_services.get_user_perm_role_in_permtenant(user_id=self.user.user_id, tenant_name=team_name)
            # teams = [{"team_identity": perm.identity} for perm in perms]
            data = dict()
            data["nick_name"] = self.user.nick_name
            data["email"] = self.user.email
            # data["teams_identity"] = teams[0]["team_identity"]
            data["teams_identity"] = perms + role_list
            data["is_user_enter_amdin"] = is_user_enter_amdin
            code = 200
            result = general_message(code, "user details query success.", "用户详情获取成功", bean=data)
            return Response(result, status=code)
        except UserNotExistError as e:
            logger.exception(e)
            code = 400
            result = general_message(code, "this user does not exist on this team.", "该用户不存在这个团队")
            return Response(result, status=code)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=500)


class UserAllTeamView(JWTAuthApiView):
    def get(self, request, *args, **kwargs):
        """
        获取当前用户所加入的所有团队
        ---

        """
        user = request.user
        code = 200
        try:
            tenants = team_services.get_current_user_tenants(user_id=user.user_id)
            if tenants:
                teams_list = list()
                for tenant in tenants:
                    teams_list.append(
                        {
                            "team_name": tenant.tenant_name,
                            "team_alias": tenant.tenant_alias,
                            "team_id": tenant.tenant_id,
                            "create_time": tenant.create_time
                        }
                    )
                result = general_message(200, "team query success", "成功获取该用户加入的团队", list=teams_list)
            else:
                teams_list = []
                result = general_message(200, "team query success", "该用户没有加入团队", bean=teams_list)
        except Exception as e:
            logger.exception(e)
            code = 400
            result = general_message(code, "failed", "请求失败")
        return Response(result, status=code)


class AddTeamView(JWTAuthApiView):
    def post(self, request, *args, **kwargs):
        """
        新建团队
        ---
        parameters:
            - name: team_alias
              description: 团队名
              required: true
              type: string
              paramType: body
            - name: useable_regions
              description: 可用数据中心 ali-sh,ali-hz
              required: false
              type: string
              paramType: body
        """
        try:
            user = request.user
            team_alias = request.data.get("team_alias", None)
            useable_regions = request.data.get("useable_regions", "")
            regions = []
            if not team_alias:
                result = general_message(400, "failed", "团队名不能为空")
                return Response(result, status=400)
            if useable_regions:
                regions = useable_regions.split(",")
            if Tenants.objects.filter(tenant_alias=team_alias).exists():
                result = general_message(400, "failed", "该团队名已存在")
                return Response(result, status=400)
            else:
                enterprise = enterprise_services.get_enterprise_by_enterprise_id(self.user.enterprise_id)
                if not enterprise:
                    return Response(general_message(500, "user's enterprise is not found"), status=500)
                code, msg, team = team_services.create_team(self.user, enterprise, regions, team_alias)

                role_obj = role_repo.get_default_role_by_role_name(role_name="owner", is_default=True)

                # 创建用户在团队的权限
                perm_info = {
                    "user_id": user.user_id,
                    "tenant_id": team.ID,
                    "enterprise_id": enterprise.pk,
                    # 创建团队时给创建用户添加owner的角色
                    "role_id": role_obj.pk
                }
                perm_services.add_user_tenant_perm(perm_info)
                for r in regions:
                    code, msg, tenant_region = region_services.create_tenant_on_region(team.tenant_name, r)
                    if code != 200:
                        return Response(general_message(code, "add team error", msg), status=code)
                return Response(general_message(200, "success", "团队添加成功", bean=team.to_dict()))
        except TenantExistError as e:
            logger.exception(e)
            code = 400
            result = general_message(code, "team already exists", "该团队已存在")
            return Response(result, status=code)
        except NoEnableRegionError as e:
            logger.exception(e)
            code = 400
            result = general_message(code, "no enable region", "无可用数据中心")
            return Response(result, status=code)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=500)


class TeamUserView(JWTAuthApiView):
    def get(self, request, team_name, *args, **kwargs):
        """
        获取某团队下的所有用户(每页展示八个用户)
        ---
        parameters:
            - name: team_name
              description: 团队名称
              required: true
              type: string
              paramType: path
            - name: page
              description: 页数
              required: true
              type: string
              paramType: query
        """
        try:
            code = 200
            page = request.GET.get("page", 1)
            # 获得租户/团队 对象
            user_list = team_services.get_tenant_users_by_tenant_name(tenant_name=team_name)
            users_list = list()
            for user in user_list:
                # 获取一个用户在一个团队中的身份列表
                perms_identitys_list = team_services.get_user_perm_identitys_in_permtenant(user_id=user.user_id,
                                                                                           tenant_name=team_name)
                # 获取一个用户在一个团队中的角色ID列表
                perms_role_list = team_services.get_user_perm_role_id_in_permtenant(user_id=user.user_id,
                                                                                    tenant_name=team_name)

                role_info_list = []

                for identity in perms_identitys_list:
                    if identity == "access":
                        role_info_list.append({"role_name": identity, "role_id": None})
                    else:
                        role_id = role_repo.get_role_id_by_role_name(identity)
                        role_info_list.append({"role_name": identity, "role_id": role_id})
                for role in perms_role_list:
                    role_name = role_repo.get_role_name_by_role_id(role)
                    role_info_list.append({"role_name": role_name, "role_id": role})

                users_list.append(
                    {
                        "user_id": user.user_id,
                        "user_name": user.nick_name,
                        "email": user.email,
                        "role_info": role_info_list
                    }
                )
            paginator = Paginator(users_list, 8)
            try:
                users = paginator.page(page).object_list
            except PageNotAnInteger:
                users = paginator.page(1).object_list
            except EmptyPage:
                users = paginator.page(paginator.num_pages).object_list
            result = general_message(code, "team members query success", "查询成功", list=users, total=paginator.count)
        except UserNotExistError as e:
            code = 400
            logger.exception(e)
            result = general_message(code, "user not exist", e.message)
        except TenantNotExistError as e:
            code = 400
            logger.exception(e)
            result = general_message(code, "tenant not exist", "{}团队不存在".format(team_name))
        except Exception as e:
            code = 500
            logger.exception(e)
            result = general_message(code, "system error", "系统异常")
        return Response(data=result, status=code)


class TeamUserAddView(JWTAuthApiView):
    def post(self, request, team_name, *args, **kwargs):
        """
        团队中添加新用户
        ---
        parameters:
            - name: team_name
              description: 团队名称
              required: true
              type: string
              paramType: path
            - name: user_ids
              description: 添加成员id 格式 {'user_ids':'1,2'}
              required: true
              type: string
              paramType: body
            - name: identitys
              description: 选择权限(当前用户是管理员'admin'或者创建者'owner'就展示权限选择列表，不是管理员就没有这个选项, 默认被邀请用户权限是'access') 格式{"identitys": "viewer,access"}
              required: true
              type: string
              paramType: body
        """
        perm_list = team_services.get_user_perm_identitys_in_permtenant(
            user_id=request.user.user_id,
            tenant_name=team_name
        )
        # 根据用户在一个团队的角色来获取这个角色对应的所有权限操作
        role_perm_tuple = team_services.get_user_perm_in_tenant(user_id=request.user.user_id, tenant_name=team_name)
        if perm_list:
            no_auth = ("owner" not in perm_list) and ("admin" not in perm_list)
        else:
            no_auth = "manage_team_member_permissions" not in role_perm_tuple
        if no_auth:
            code = 400
            result = general_message(code, "no identity", "您不是管理员，没有权限做此操作")
            return Response(result, status=code)
        try:
            user_ids = request.data.get('user_ids', None)
            identitys = request.data.get('identitys', None)
            identitys = identitys.split(',') if identitys else []
            if not user_ids:
                raise ParamsError("用户名为空")
            code = 200
            team = team_services.get_tenant_by_tenant_name(tenant_name=team_name, exception=True)
            user_ids = user_ids.split(',')
            if identitys:
                team_services.add_user_to_team(request=request, tenant=team, user_ids=user_ids, identitys=identitys)
                result = general_message(code, "success", "用户添加到{}成功".format(team_name))
            else:
                team_services.add_user_to_team(request=request, tenant=team, user_ids=user_ids, identitys='access')
                result = general_message(code, "success", "用户添加到{}成功".format(team_name))
        except PermTenantsExistError as e:
            code = 400
            result = general_message(code, "permtenant exist", e.message)
        except ParamsError as e:
            logging.exception(e)
            code = 400
            result = general_message(code, "params user_id is empty", e.message)
        except UserNotExistError as e:
            code = 400
            result = general_message(code, "user not exist", e.message)
        except Tenants.DoesNotExist as e:
            code = 400
            logger.exception(e)
            result = general_message(code, "tenant not exist", "{}团队不存在".format(team_name))
        except UserExistError as e:
            logger.exception(e)
            code = 400
            result = general_message(code, "user already exist", e.message)
        except Exception as e:
            code = 500
            logger.exception(e)
            print(str(e))
            result = general_message(code, "system error", "系统异常")
        return Response(result, status=code)


class UserDelView(JWTAuthApiView):
    def delete(self, request, team_name, *args, **kwargs):
        """
        删除租户内的用户
        (可批量可单个)
        ---
        parameters:
            - name: team_name
              description: 团队名称
              required: true
              type: string
              paramType: path
            - name: user_ids
              description: 用户名 user_id1,user_id2 ...
              required: true
              type: string
              paramType: body
        """
        try:
            identitys = team_services.get_user_perm_identitys_in_permtenant(
                user_id=request.user.user_id,
                tenant_name=team_name
            )

            perm_tuple = team_services.get_user_perm_in_tenant(user_id=request.user.user_id, tenant_name=team_name)

            if "owner" not in identitys and "admin" not in identitys and "manage_team_member_permissions" not in perm_tuple:
                code = 400
                result = general_message(code, "no identity", "没有权限")
                return Response(result, status=code)

            user_ids = str(request.data.get("user_ids", None))
            if not user_ids:
                result = general_message(400, "failed", "删除成员不能为空")
                return Response(result, status=400)

            try:
                user_id_list = [int(user_id) for user_id in user_ids.split(",")]
            except Exception as e:
                logger.exception(e)
                result = general_message(200, "Incorrect parameter format", "参数格式不正确")
                return Response(result, status=400)

            if request.user.user_id in user_id_list:
                result = general_message(400, "failed", "不能删除自己")
                return Response(result, status=400)

            for user_id in user_id_list:
                print user_id
                role_name_list = team_services.get_user_perm_role_in_permtenant(user_id=user_id, tenant_name=team_name)
                identity_list = team_services.get_user_perm_identitys_in_permtenant(user_id=user_id,
                                                                                    tenant_name=team_name)
                print role_name_list
                if "owner" in role_name_list or "owner" in identity_list:
                    result = general_message(400, "failed", "不能删除团队创建者！")
                    return Response(result, status=400)
            try:
                user_services.batch_delete_users(team_name, user_id_list)
                result = general_message(200, "delete the success", "删除成功")
            except Tenants.DoesNotExist as e:
                logger.exception(e)
                result = generate_result(400, "tenant not exist", "{}团队不存在".format(team_name))
            except Exception as e:
                logger.exception(e)
                result = error_message(e.message)
            return Response(result)
        except Exception as e:
            code = 500
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=code)


class TeamNameModView(JWTAuthApiView):
    def post(self, request, team_name, *args, **kwargs):
        """
        修改团队名
        ---
        parameters:
            - name: team_name
              description: 旧团队名
              required: true
              type: string
              paramType: path
            - name: new_team_alias
              description: 新团队名
              required: true
              type: string
              paramType: body
        """
        try:
            perms = team_services.get_user_perm_identitys_in_permtenant(
                user_id=request.user.user_id,
                tenant_name=team_name
            )
            perm_tuple = team_services.get_user_perm_in_tenant(user_id=request.user.user_id, tenant_name=team_name)

            no_auth = True

            if "owner" in perms or "modify_team_name" in perm_tuple:
                no_auth = False

            if no_auth:
                code = 400
                result = general_message(code, "no identity", "权限不足不能修改团队名")
            else:
                new_team_alias = request.data.get("new_team_alias", "")
                if new_team_alias:
                    try:
                        code = 200
                        team = team_services.update_tenant_alias(tenant_name=team_name, new_team_alias=new_team_alias)
                        result = general_message(code, "update success", "团队名修改成功", bean=team.to_dict())
                    except Exception as e:
                        code = 500
                        result = general_message(code, "update failed", "团队名修改失败")
                        logger.exception(e)
                else:
                    result = general_message(400, "failed", "修改的团队名不能为空")
                    code = 400
        except Exception as e:
            code = 500
            result = general_message(code, "update failed", "团队名修改失败")
            logger.exception(e)
        return Response(result, status=code)


class TeamDelView(JWTAuthApiView):
    def delete(self, request, team_name, *args, **kwargs):
        """
        删除当前团队
        ---
        parameters:
            - name: team_name
              description: 要删除的团队
              required: true
              type: string
              paramType: path
        """
        code = 200

        identity_list = team_services.get_user_perm_identitys_in_permtenant(
            user_id=request.user.user_id,
            tenant_name=team_name
        )
        perm_tuple = team_services.get_user_perm_in_tenant(user_id=request.user.user_id, tenant_name=team_name)

        if "owner" not in identity_list and "drop_tenant" not in perm_tuple:
            code = 400
            result = general_message(code, "no identity", "您不是最高管理员，不能删除团队")
            return Response(result, status=code)

        try:
            service_count = team_services.get_team_service_count_by_team_name(team_name=team_name)
            if service_count >= 1:
                result = general_message(400, "failed", "当前团队内有应用,不可以删除")
                return Response(result, status=400)
            status = team_services.delete_tenant(tenant_name=team_name)
            if not status:
                result = general_message(code, "delete a tenant successfully", "删除团队成功")
            else:
                code = 400
                result = general_message(code, "delete a tenant failed", "删除团队失败")
        except Tenants.DoesNotExist as e:
            code = 400
            logger.exception(e)
            result = generate_result(code, "tenant not exist", "{}团队不存在".format(team_name))
        except Exception as e:
            code = 500
            result = general_message(code, "sys exception", "系统异常")
            logger.exception(e)
        return Response(result, status=code)


class TeamInvView(JWTAuthApiView):
    def get(self, request, team_name, *args, **kwargs):
        """
        邀请注册，弹框的详情
        ---
        parameters:
            - name: team_name
              description: 邀请进入的团队id
              required: true
              type: string
              paramType: path
        """
        try:
            team = team_services.get_tenant_by_tenant_name(tenant_name=team_name)
            team_id = str(team.ID)
            data = dict()
            data["register_type"] = "invitation"
            data["value"] = team_id
            result = general_message(200, "success", "成功获得邀请码", bean=data)
            return Response(result, status=200)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=500)


class TeamExitView(JWTAuthApiView):
    def get(self, request, team_name, *args, **kwargs):
        """
        退出当前团队
        ---
        parameters:
            - name: team_name
              description: 当前所在的团队
              required: true
              type: string
              paramType: path
        """

        identity_list = team_services.get_user_perm_identitys_in_permtenant(
            user_id=request.user.user_id,
            tenant_name=team_name
        )

        role_name_list = team_services.get_user_perm_role_in_permtenant(user_id=request.user.user_id,
                                                                        tenant_name=team_name)

        if "owner" in identity_list:
            result = general_message(409, "not allow exit.", "您是当前团队创建者，不能退出此团队")
            return Response(result, status=409)
        if "admin" in identity_list:
            result = general_message(409, "not allow exit.", "您是当前团队管理员，不能退出此团队")
            return Response(result, status=409)

        if "owner" in role_name_list:
            result = general_message(409, "not allow exit.", "您是当前团队创建者，不能退出此团队")
            return Response(result, status=409)
        if "admin" in role_name_list:
            result = general_message(409, "not allow exit.", "您是当前团队管理员，不能退出此团队")
            return Response(result, status=409)

        try:
            code, msg_show = team_services.exit_current_team(team_name=team_name, user_id=request.user.user_id)
            if code == 200:
                result = general_message(code=code, msg="success", msg_show=msg_show)
            else:
                result = general_message(code=code, msg="failed", msg_show=msg_show)
        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
        return Response(result, status=result["code"])


class TeamDetailView(JWTAuthApiView):
    def get(self, request, team_name, *args, **kwargs):
        """
        获取团队详情
        ---
        parameters:
            - name: team_name
              description: team name
              required: true
              type: string
              paramType: path
        """
        try:

            tenant = team_services.get_tenant_by_tenant_name(team_name)
            if not tenant:
                return Response(general_message(404, "team not exist", "团队{0}不存在".format(team_name)), status=404)
            user_team_perm = team_services.get_user_perms_in_permtenant(self.user.user_id, team_name)
            tenant_info = dict()
            team_region_list = region_services.get_region_list_by_team_name(request=request,
                                                                            team_name=team_name)
            p = PermActions()
            tenant_info["team_id"] = tenant.ID
            tenant_info["team_name"] = tenant.tenant_name
            tenant_info["team_alias"] = tenant.tenant_alias
            tenant_info["limit_memory"] = tenant.limit_memory
            tenant_info["pay_level"] = tenant.pay_level
            tenant_info["region"] = team_region_list
            tenant_info["creater"] = tenant.creater
            tenant_info["create_time"] = tenant.create_time

            if not user_team_perm:
                if not self.user.is_sys_admin and team_name != "grdemo":
                    return Response(general_message(403, "you right to see this team", "您无权查看此团队"), 403)
            else:
                perms_list = team_services.get_user_perm_identitys_in_permtenant(user_id=self.user.user_id,
                                                                                 tenant_name=tenant.tenant_name)
                role_name_list = team_services.get_user_perm_role_in_permtenant(user_id=self.user.user_id,
                                                                                tenant_name=tenant.tenant_name)

                role_perms_tuple = team_services.get_user_perm_in_tenant(user_id=self.user.user_id,
                                                                         tenant_name=tenant.tenant_name)

                tenant_actions = ()
                tenant_info["identity"] = perms_list + role_name_list
                if perms_list:
                    final_identity = get_highest_identity(perms_list)
                    perms = p.keys('tenant_{0}_actions'.format(final_identity))
                    tenant_actions += perms
                tenant_actions += role_perms_tuple
                tenant_info["tenant_actions"] = tuple(set(tenant_actions))

            return Response(general_message(200, "success", "查询成功", bean=tenant_info), status=200)

        except Exception as e:
            logger.exception(e)
            result = error_message(e.message)
            return Response(result, status=result["code"])
