# 私聊监视与到点提醒（chat_watch.py / push_reminder.py 唯一权威）

> **职责**：私聊未读监视常驻进程与货轮/商船到点提醒计划任务的启动、停止、注册、
> 删除，及其互斥/防重推规则。
> **何时读取**：用户说"开启/关闭私聊监视/私聊提醒"、"开启/关闭货轮提醒/商船
> 提醒/到点提醒"，或排查"为什么没推送提醒"时。

## 私聊未读监视（chat_watch.py，常驻后台进程）

`scripts/chat_watch.py`：每 2 分钟一轮检测游戏内私聊未读红点（tick 相位对齐偶数分钟
**:30 秒**，错开整点触发的贸易/资源检查），发现未读**直接推送提醒**（不再经
agent 轮询，0 token）：

- **互斥让位（私聊监视优先级最低，其他任务优先运行）**：闯关/城战领取序列
  在后台运行（其 PID 文件存在）→ 本轮跳过；另每轮检测前枚举 python/pythonw
  进程命令行（PowerShell CIM，本机 wmic 已移除），命中占设备脚本名单
  （check_main/check_ships/check_res/gather_res/claim_online_reward/claim_seq/
  battle_run/start_game/stop_game/force_main/status_check，排除自身）→ 记
  "<脚本名> 运行中, 私聊监视让位" 跳过本轮；枚举失败也保守跳过本轮（记 WARN）。
  game_status（只读 adb）与 push_reminder（无截屏无点击）不占设备不入名单；
  新增占设备脚本时须同步加入名单（chat_watch.py 顶部 DEVICE_SCRIPTS）；
- **主界面守卫（零点击原则）**：不在主界面（game_lib.on_main 四条件判定）→ 记
  "非主界面(设备可能正被使用), 零点击跳过本轮" 直接跳过，**绝不主动点击退回**
  （2026-10-17 曾因旧版"层层退回恢复"在采集进行时退掉采集画面致资源误读，
  遂废弃该逻辑）；卡子页面的恢复由每 30 分钟贸易/资源会话的 check_main
  负责，监视只在主界面做检测；
- **检测动作（两层）**：第一层粗筛主界面聊天入口未读红点（复用主界面判定的
  同一张截图采样，无红点**零点击**直接结束本轮）；有红点才第二层确认：进聊天页 →
  切私聊页签 → 截屏采样私聊页签红点 → 返回主界面（逐次点返回键并复检，每次
  间隔 0.8 秒，最多 3 次；恢复失败不强制，下轮重试）；
- **推送规则**：日间经 `game_lib.push_weixin()` 直推"海岛私聊有未读消息"（内置
  30 秒推送锁，失败自动短时重试默认 3 次）；夜间只写夜间日志
  `$TEMP/fkssj_night_events.log`（任务名"私聊"），
  由 08:04 夜间总结推送任务统一推送；
- **防重推**：红点持续存在只推一次；红点消失后重置，来新消息可再推；日间直推
  失败不置已提醒标志，下轮自动重试；
- **单轮异常**自动捕获，进程不退出，下一轮继续。
- PID 文件 `$TEMP/fkssj_chat_watch.pid`；日志 `$TEMP/fkssj_chat_watch.log` /
  `.err.log`。

### 启动（必须后台启动，同闯关的 PowerShell 分离启动器形式）

```text
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "<启动器路径>"
```

启动器为只含一条 `Start-Process` 的 .ps1（**注释必须纯 ASCII**，原因见
`references/battle.md` 启动节；首次开启时按本模板生成 `local/launch_chat_watch.ps1`）：

```text
Start-Process -FilePath "<PYTHON>" -ArgumentList '"<SKILL_DIR>/scripts/chat_watch.py"' -WindowStyle Hidden -RedirectStandardOutput "$env:TEMP\fkssj_chat_watch.log" -RedirectStandardError "$env:TEMP\fkssj_chat_watch.err.log"
```

启动后等待约 5 秒确认 `$TEMP/fkssj_chat_watch.pid` 存在：存在 → 汇报"私聊监视已
启动"；不存在 → `tail -n 10 "$TEMP/fkssj_chat_watch.log"` 按输出规范汇报启动失败
（日志无新内容时先查启动器是否含非 ASCII 字节）。启动前 PID 文件已存在 → 在跑，
不重复启动。

> **调用方式（2026-10-17 实测）**：`powershell.exe -File <启动器>` 在 Hermes 终端里
> 前台调用会挂住直到超时（bash 等 Start-Process 继承的句柄），但子进程已正常启动。
> 因此该命令一律用 `background=true` 发起，再用第二条命令查 PID 文件，不要前台等返回。

### 停止

```text
<PYTHON> <SKILL_DIR>/scripts/chat_watch.py --stop
```

### 触发词

- "开启私聊监视/私聊提醒" → 按上文启动；
- "关闭私聊监视/私聊提醒" → 按上文停止；
- 监视是常驻进程（非 cron），**电脑重启后不会自启**，需重新执行启动步骤。

## 货轮/商船到点提醒（push_reminder.py，Windows 计划任务）

`scripts/push_reminder.py`：纯提醒脚本（**不占设备**：无截屏无点击无游戏交互），
按内置时刻表直推微信：

- 货轮：每天 8-22 点每小时"搁浅的货轮已在世界刷新!"
- 商船：每天 8/11/14/17/20/23 点"联盟商船刷新!"
- 同刻（8/11/14/17/20 点）合并一条；其余小时（含夜间）静默退出不推送；
- **停用清单**：`$TEMP/fkssj_reminder_off` 一行列出**已停用**的提醒名（`cargo`
  货轮 / `ship` 商船，空格或逗号分隔）；缺省、读取失败或未知词 = 全部照推；
  切换只改这个文件，不必改代码、不必重注册计划任务；后续新增提醒类型只需
  起新名字照旧入列（清单式拓展，无需扩枚举值）；
- 推送经 `game_lib.push_weixin()`（内置 30 秒推送锁，与闯关/领取/私聊等直推
  互挤时自动错开）；直推失败多为撞上 iLink 微信通道 30 秒全局冷却（与对话
  回复/cron 投递共享），失败后约 40 秒重试 1 次，仍失败下次整点照常。

由 Windows 计划任务每小时整点唤醒（取代原 Hermes /cron 货轮/商船任务，0 token；
"提醒类任务是游戏刷新时间，固定不可改"）。

### 注册（"开启货轮提醒/商船提醒"）

```text
schtasks /Create /TN "fkssj_push_reminder" /TR "\"<PYTHONW>\" \"<SKILL_DIR>\scripts\push_reminder.py\"" /SC HOURLY /ST 00:00 /F
```

- `<PYTHONW>` 用 pythonw.exe 完整路径（无控制台窗口；脚本已适配 stdout 为 None
  的场景）；`<SKILL_DIR>` 为 skill 安装目录；
- 注册后手动跑一次验证：`<PYTHON> <SKILL_DIR>/scripts/push_reminder.py`
  （非整点输出 `SKIP: 非整点…` 即守卫生效；要实际推一条加 `--force`）；
- **整点守卫（2026-10-17 新增，同日随停用清单重排）**：脚本先按停用清单与时刻表
  算出本小时是否有要推的提醒（全停或本小时无提醒直接静默退出）；有提醒且分钟 > 10
  又未带 `--force` 时才 `SKIP: 非整点…` 退出、不推送——提醒文案是固定话术，在
  17:24 这类非整点手动跑会推出“假刷新”提醒，误导用户。计划任务整点唤醒在 10 分钟
  内均正常推送，需要非整点立即验证时加 `--force`。
- 计划任务错过整点（关机/睡眠）不补触发，错过即错过，下一整点照常——提醒类
  可接受。

### 删除（"关闭货轮提醒/商船提醒"）

```text
schtasks /Delete /TN "fkssj_push_reminder" /F
```

货轮与商船共用一个计划任务（`fkssj_push_reminder`），**单独开关其一不改计划任务**：
往 `$TEMP/fkssj_reminder_off` 清单写对应提醒名即停用（`ship`=停商船只推货轮，
`cargo`=停货轮只推商船，`cargo ship`=两类都停、计划任务照常唤醒但静默退出）；把
名字从清单删掉或清空文件即恢复。彻底关闭提醒设施才用上面的删除命令；重新开启时
按上文重新注册（清单不影响注册状态，保留原值即可）。

## 排查

- **所有脚本直推都失败（`$TEMP/fkssj_push.log` 连续出现 fail 行且重试无效）**：`game_lib.push_weixin()` 老实现
  直接 `subprocess.run(['hermes', 'send', ...])`；本机 PATH 上的 `hermes` 是 Git Bash
  无扩展名脚本，Windows CreateProcess 不能执行（WinError 2），于是恒判失败。
  2026-10-17 已修：新增 `_hermes_send_argv()` 优先解析 `hermes.cmd` 并经 `cmd /c` 调用，
  消息改为经 stdin（`-f -`）传入以避开 `%` / `&` / 引号转义；成功判定改为
  `rc==0 且 (stdout 含 "Sent to" 或 JSON 含 "success": true)`。修改 game_lib 后
  **常驻进程需重启才生效**（chat_watch --stop 后重新启动）。换机复现时先确认
  `shutil.which('hermes.cmd')` 有值。
- **整点没收到货轮/商船提醒**：`schtasks /Query /TN "fkssj_push_reminder"` 看
  上次运行时间与结果；再手动跑一次脚本看 RESULT 行；
- **推送锁冲突属正常**：多条直推同时抢 30 秒锁会顺次送达（后到者等满 30 秒），
  延迟最多 30 秒量级，不必处理；
- **私聊有红点但没提醒**：`tail -n 20 "$TEMP/fkssj_chat_watch.log"` 看最近几轮
  是"跳过"（互斥/非主界面，正常）还是检测/推送失败；
- **日志里连续多轮"非主界面"**：属正常让位（零点击跳过，见上文主界面守卫）——
  设备正被其他任务使用或用户在玩；游戏确实停在子页面时由下一轮贸易/资源
  会话的 check_main 恢复，长期未恢复再手动跑 `scripts/check_main.py`
  （单轮进出约 13 秒，回主界面 nav_score=1.00）；
- 私聊检测依赖固定的入口/页签坐标与红点参考色，**换分辨率或游戏改版后需重新
  校准**（常量在 `scripts/chat_watch.py` 顶部）。
