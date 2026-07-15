# MyJob 浏览器侧平台桥接

该扩展在用户自己的 Chrome 或 Microsoft Edge 中运行。招聘平台登录态、岗位操作、消息同步和窗口控制不会经过 MyJob 后端。

## 安装

1. Chrome 打开 `chrome://extensions/`，Edge 打开 `edge://extensions/`。
2. 开启开发者模式。
3. 点击“加载已解压的扩展”，选择本目录 `browser_extension`。
4. 保持扩展启用，然后刷新 MyJob 工作台。

## 数据边界

- 招聘平台 Cookie 只由浏览器保存。
- 岗位、投递、会话、计划和平台统计保存在 MyJob 页面域名下的 IndexedDB。
- 后端只处理 MyJob 账号、管理员和用户简历，不接收招聘平台数据。
- 验证码、滑块、安全验证和平台风控必须由用户人工处理。
