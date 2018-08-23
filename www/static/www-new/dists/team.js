webpackJsonp([4],{103:function(module,exports,__webpack_require__){"use strict";function noop(){}function AppLogSocket(option){option=option||{},this.url=option.url,this.instanceId=(option.instanceId||"").substring(0,12),this.serviceId=option.serviceId,this.onOpen=option.onOpen||noop,this.onMessage=option.onMessage||noop,this.onError=option.onError||noop,this.onClose=option.onClose||noop,this.onError=option.onError||noop,this.onSuccess=option.onSuccess||noop,this.onComplete=option.onComplete||noop,this.onFail=option.onFail||noop,this.isAutoConnect=option.isAutoConnect,this.init()}Object.defineProperty(exports,"__esModule",{value:!0});var _timerQueue=__webpack_require__(60),_timerQueue2=function(obj){return obj&&obj.__esModule?obj:{default:obj}}(_timerQueue);AppLogSocket.prototype={constructor:AppLogSocket,init:function(){this.webSocket=new WebSocket(this.url),this.webSocket.onopen=this._onOpen.bind(this),this.webSocket.onmessage=this._onMessage.bind(this),this.webSocket.onclose=this._onClose.bind(this),this.webSocket.onerror=this._onError.bind(this),this.timerQueue=new _timerQueue2.default({onExecute:this.onMessage})},getSocket:function(){return this.webSocket},close:function(){this.webSocket.close()},_onOpen:function(evt){this.serviceId&&this.webSocket.send("topic="+this.serviceId),this.onOpen()},_onMessage:function(evt){if(evt.data&&"ok"!==evt.data){var msg=evt.data;msg=this.instanceId?msg.substring(0,12)===this.instanceId?"<p>"+msg.substr(13)+"</p>":"":"<p>"+msg+"</p>",msg&&this.timerQueue.add(msg)}},_onClose:function(evt){this.onClose()},_onError:function(){this.onError()}},exports.default=AppLogSocket},197:function(module,exports,__webpack_require__){"use strict";function _interopRequireDefault(obj){return obj&&obj.__esModule?obj:{default:obj}}Object.defineProperty(exports,"__esModule",{value:!0});var _pageController=__webpack_require__(17),_pageController2=_interopRequireDefault(_pageController),_teamApiCenter=__webpack_require__(106),_appLogSocket=(__webpack_require__(20),__webpack_require__(103)),_widget=(_interopRequireDefault(_appLogSocket),__webpack_require__(4)),_widget2=_interopRequireDefault(_widget),_validationUtil=__webpack_require__(61),_validationUtil2=_interopRequireDefault(_validationUtil),_pageAppApiCenter=__webpack_require__(19),template=__webpack_require__(212),Msg=_widget2.default.Message,Team=(0,_pageController2.default)({template:template,property:{tenantName:"",renderData:{pageData:{}}},method:{getInitData:function(){var _this=this;(0,_pageAppApiCenter.getPageTeamData)(this.tenantName).done(function(pageData){_this.renderData.pageData=pageData,_this.render()})},handleInvite:function(email,perm){var self=this;(0,_teamApiCenter.addMember)(this.tenantName,email,perm).done(function(){self.onInviteSuccess()})},onInviteSuccess:function(){$("#invite_email").val(""),this.getInitData()},handleSetPerm:function(user,perm,checked){return checked?(0,_teamApiCenter.setMemberPerm)(this.tenantName,user,perm):(0,_teamApiCenter.removeMemberPerm)(this.tenantName,user)},handleRemoveMember:function(user){(0,_teamApiCenter.removeMember)(this.tenantName,user).done(function(data){$("tr[entry-user="+user+"]").remove()})},showRemoveConfirm:function(user){var self=this,confirm=_widget2.default.create("confirm",{title:" 删除成员 "+user,content:"确定要执行此操作吗？",event:{onOk:function(){confirm.destroy(),self.handleRemoveMember(user)}}})}},domEvents:{"#invite_user_btn click":function(){var email=$("#invite_email").val(),perm=$("#ivite_perm").val();if(!_validationUtil2.default.valid("email",email))return Msg.warning("邮箱格式不正确，请检查后重试"),!1;this.handleInvite(email,perm)},".js-perm click":function(e){var $target=$(e.currentTarget);if(!$target.attr("disabled")){var checked=$target.prop("checked"),perm=$target.attr("identity"),user=$target.parents("tr").attr("entry-user"),next_identities=$target.parent().nextAll();this.handleSetPerm(user,perm,checked).done(function(data){checked?next_identities.children("input").prop("checked",!0).prop("disabled",!0):next_identities.each(function(){var $input=$(this).find("input");"access"!=$input.attr("identity")&&$input.prop("checked",!1).prop("disabled",!1)})}).fail(function(){checked?$target.removeAttr("checked"):$target.prop("checked","checked")})}},".member-remove click":function(e){var $target=$(e.currentTarget),user=$target.parents("tr").attr("entry-user");this.showRemoveConfirm(user)}},onReady:function(){this.renderData.tenantName=this.tenantName,this.getInitData()}});window.TeamController=Team,exports.default=Team},212:function(module,exports){module.exports='{{if pageData.actions[\'perm_setting\']}}\n<section class="panel panel-default">\n    <div class="panel-heading">\n        <h3 class="panel-title">团队成员</h3>\n    </div>\n    <div class="panel-body">\n        \x3c!-- search start --\x3e\n        {{if pageData.team_invite}}\n        <form class="form-inline" style="padding:20px 0">\n            <div class="form-group">\n              <input type="text" class="email-invite form-control" id="invite_email" name="invite_email" placeholder="邮件地址">\n            </div>\n            <div class="form-group">\n                <select class="form-control" id="ivite_perm" name="ivite_perm">\n                    <option value="access">访问</option>\n                    <option value="viewer">观察者</option>\n                    <option value="developer">开发者</option>\n                    <option value="admin">管理员</option>\n                </select>\n            </div>\n            <button type="button" class="btn btn-success" id="invite_user_btn">邀请</button>\n        </form>\n        {{/if}}\n        \x3c!-- search end --\x3e\n        \x3c!-- table start --\x3e\n        <div role="tabpanel" id="permission">\n            <div id="action_report">\n                <table perm-type="tenant" class="table">\n                    <thead>\n                        <tr class="active">\n                            <th>成员</th>\n                            <th class="text-center">管理员</th>\n                            <th class="text-center">开发者</th>\n                            <th class="text-center">观察者</th>\n                            <th class="text-center">访问</th>\n                            <th class="text-center">移除权限</th>\n                        </tr>\n                    </thead>\n                    <tbody>\n                        {{each pageData.team_users || []}}\n                        <tr entry-user="{{$value.name}}">\n                            <td>{{$value.name}} {{$value.selfuser ? \'(本人)\' : \'\'}}</td>\n                            <td class="perm-modify-enable text-center">\n                                <input class="js-perm" type="checkbox" identity="admin"\n                                {{$value.adminCheck ? \'checked\' : \'\'}} \n                                {{$value.selfuser ? \'disabled\': \'\'}}\n                                />\n                            </td>\n                            <td class="perm-modify-enable text-center">\n                                <input class="js-perm" type="checkbox" identity="developer" \n                                {{$value.developerCheck ? \'checked\':\'\'}}\n                                {{($value.developerDisable || $value.selfuser) ? \'disabled\' : \'\'}}\n                            </td>\n                            <td class="perm-modify-enable text-center">\n                                <input class="js-perm" type="checkbox" identity="viewer" \n                                {{$value.viewerCheck ? \'checked\':\'\'}}\n                                {{($value.viewerDisable || $value.selfuser) ? \'disabled\' : \'\'}}\n                            </td>\n                            <td class="text-center">\n                                <input class="js-perm" type="checkbox" identity="access" checked="" disabled="">\n                            </td>\n                            <td class="text-center">\n                                {{if !$value.selfuser}}\n                                    <a class="member-remove"><i class="glyphicon glyphicon-remove"></i></a>\n                                {{/if}}\n                            \n                            </td>\n                        </tr>\n                        {{/each}}\n                    </tbody>\n                </table>\n            </div>\n            <div class="alert alert-warning">\n                <strong>权限体系:</strong>\n                <p>平台管理员 - 平台所有权限</p>\n                <p>服务管理员 - 服务所有权限，需要关联服务</p>\n                <p>开发者 - 代码上传权限，需要关联服务</p>\n                <p>观察者 - 只读权限，需要关联服务</p>\n            </div>\n        </div>\n        \x3c!-- table end --\x3e\n    </div>\n</section>\n{{else}}\n<p class="alert alert-warning">无权限</p>\n{{/if}}'},542:function(module,exports,__webpack_require__){module.exports=__webpack_require__(197)},59:function(module,exports,__webpack_require__){"use strict";function Queue(){this.datas=[]}Object.defineProperty(exports,"__esModule",{value:!0}),Queue.prototype={constructor:Queue,push:function(data){void 0!==data&&this.datas.push(data)},shift:function(){return this.datas.shift()},getCount:function(){return this.datas.length},empty:function(){return 0===this.datas.length}},exports.default=Queue},60:function(module,exports,__webpack_require__){"use strict";function TimerQueue(option){option=option||{},this.queue=new _queue2.default,this.timer=null,this.isStarted=!1,this.interval=option.interval||300,this.onExecute=option.onExecute||util.noop}Object.defineProperty(exports,"__esModule",{value:!0});var _queue=__webpack_require__(59),_queue2=function(obj){return obj&&obj.__esModule?obj:{default:obj}}(_queue);TimerQueue.prototype={add:function(data){this.queue.push(data),this.isStarted||this.start()},start:function(){var self=this;this.timer=setInterval(function(){self.queue.empty()?self.stop():self.execute()},this.interval)},stop:function(){this.isStarted=!1,clearInterval(this.timer)},execute:function(){this.onExecute(this.queue.shift())}},exports.default=TimerQueue}},[542]);