# Bemfa WOL
巴法云远程开机工具，可接入小爱同学等语音助手

## 功能
- 远程开机
- 远程关机
- 定时同步电脑状态到巴法云，用于通过语音助手查询电脑开关机状态


## 使用方法

### 配置巴法云
1. 注册并登录[巴法云](https://cloud.bemfa.com/)，复制并保存好私钥
2. 选择 TCP 创客云，新建主题：如PC001。（名称最后三位数字为固定值，不可更改）
3. 巴法云接入[文档](https://cloud.bemfa.com/docs/#/)

### 配置电脑
1. 远程开机电脑启用 WOL 功能，详细可参考电脑说明书或主板说明书
2. 开启休眠功能（脚本中的关机功能实际为休眠，可修改为关机或睡眠）
    ```bash
    # CMD 下管理员身份执行
    powercfg.exe /hibernate on
    ```
3. [安装 OpenSSH](https://learn.microsoft.com/zh-cn/windows-server/administration/openssh/openssh_install_firstuse?tabs=gui) 服务，并设置为开机自启。

### 配置服务器
1. 局域网中配置一台用于部署 Bemfa WOL 的服务器，可以是主机、树莓派、NAS等。
2. 在服务器上安装 python 环境，配置 SSH 密钥，并将公钥复制到远程开机电脑的 `authorized_keys` 文件中。
管理员用户的文件路径：C:\ProgramData\ssh\administrators_authorized_keys
普通用户的文件路径：C:\Users\用户名\.ssh\authorized_keys
详细内容参考[此处](https://learn.microsoft.com/zh-cn/windows-server/administration/openssh/openssh_keymanagement#host-key-generation)

3. 填写 `wakeup.py` 中参数，然后复制到服务器上。
    | 参数 | 作用 |
    | -- | -- |
    | **client_id** | 巴法云私钥 |
    | **topid** | 巴法云主题名称 |
    | **pc_user** | 远程开机电脑的用户名 |
    | **pc_ip** | 远程开机电脑的IP (设置一个固定 IP) |
    | **mac** | 远程开机电脑的 MAC 地址 |

4. 运行 `wakeup.py` 脚本（建议设置为服务，保持在后台运行）

### 推送消息
在巴法云主题的消息框中输入 `on` 或 `off` 并推送消息，可实现远程开机或关机。

### 接入小爱同学和米家
- 进入米家 App -> 我的 -> 添加其他平台 -> 选择“巴法” -> 登录巴法云账号 -> 同步设备。
    - 对小爱同学说：打开电脑（开机）
    - 对小爱同学说：关闭电脑（关机）
    - 对小爱同学说：查询电脑状态（查询电脑是否开机）

- 米家添加手动控制 -> 添加执行动作选 `设备 - 小爱音箱 - 自定义指令` -> 设置开机指令的名称（不要设置成“打开电脑”，好像不起作用）。同样方法再设置一个关机的指令。这样可实现在米家APP中控制电脑开关机。