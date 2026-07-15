# MyJob 前后端与用户侧平台边界

## 强制规则

招聘平台相关操作和数据必须位于用户侧。后续功能也必须遵守该规则。

| 用户侧 Vue 与扩展 | FastAPI 后端 |
|---|---|
| 平台登录检测、登录窗口、全部登出、停止窗口 | MyJob 注册、登录、会话与密码 |
| 岗位搜索、页面解析、筛选与投递 | 管理员账号、注册开关与在线统计 |
| 会话同步、消息发送和微信记录 | 主简历保存、模板、导入与导出 |
| 求职计划运行和自动化边界 | Vue 静态文件与 HTTPS |
| IndexedDB 保存全部平台业务数据 | 不接收、不保存平台业务数据 |

## 用户侧链路

1. Vue 页面通过 `window.postMessage` 向 MyJob 扩展内容脚本发出请求。
2. 内容脚本使用 `chrome.runtime.sendMessage` 交给扩展 Service Worker。
3. Service Worker 控制招聘平台标签页或窗口。
4. 招聘平台 Content Script 在页面内检测登录态、读取岗位和执行用户发起的操作。
5. 返回结果由 Vue 写入当前 MyJob 域名下的 IndexedDB。

普通 Vue 页面不直接访问招聘平台 DOM，也不读取平台 Cookie。扩展只在清单声明的 MyJob 本地域名和四个招聘平台域名运行。

## 本地存储

IndexedDB 数据库 `myjob-client-platform-data` 包含：

- `jobs`
- `conversations`
- `messages`
- `campaigns`
- `exchanges`
- `tailored`
- `meta`

这些数据不通过 REST API 或 WebSocket 上传。刷新页面和重启浏览器后数据仍可用，清理该站点浏览器数据时会被删除。

## 后端接口白名单

- `/api/auth/*`
- `/api/admin/*`
- `/api/resume-templates*`
- `/api/resumes/master*`
- `/api/health`

新增后端路由时必须检查请求和响应是否包含招聘平台 Cookie、URL、岗位、公司、投递、会话、招聘者、计划或平台统计。包含任意此类数据的功能必须改为浏览器侧实现。

## 合规要求

- 不绕过验证码、滑块、安全验证或平台风控。
- 检测到风控提示时停止自动操作并提示用户人工处理。
- 已登录平台不会重复打开登录窗口。
- 全部登出清除四个平台浏览器侧会话。
- 停止操作关闭所有招聘平台窗口。
- 自动投递需要用户明确确认并执行本地每日上限。

## 部署

轻量服务器只承载账号、管理员、简历和静态 Vue 文件：

```powershell
python myjob_server.py --host 0.0.0.0 --port 8010 `
  --ssl-certfile C:\path\fullchain.pem `
  --ssl-keyfile C:\path\privkey.pem
```

招聘平台扩展和 IndexedDB 始终运行在用户自己的 Chrome 或 Edge 中，不部署到服务器。
