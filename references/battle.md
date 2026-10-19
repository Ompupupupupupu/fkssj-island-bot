# 自动闯关（battle_run.py 唯一权威）

> **职责**：闯关的启动、停止、战果汇报与让位规则。
> **何时读取**：用户说"闯关/打关卡/继续打"、"停止闯关/别打了"，需要闯关战果，
> 或处理闯关与其他任务冲突时。

## 脚本行为

`scripts/battle_run.py`：自动闯关长跑（**必须后台启动**）：开战 12 秒后跳过看结果，
胜→直接下一关，败→再战；连续 5 败或单场超 15 分钟告警退出（告警只打印 [ALERT] 行，
不弹窗，由 agent 转告用户）；**任何退出路径（告警/中断/异常）结束后自动调
check_main.py 恢复主界面并自动推送战果**（日间直推微信/夜间写夜间日志，见下文
"结果自动推送"）；启动写 PID 文件（`$TEMP/fkssj_battle.pid`），`--stop` 按 PID
停止后台闯关；启动时同时创建战果标记 `$TEMP/fkssj_battle_done.pending`
（直推失败时的兜底信号）。

- 参数：可选 `--stop`
- exit code：0=结束且回主界面成功 / 未在运行时停止成功；1=异常、回主界面失败或停止失败

## 启动（必须后台启动，防会话超时）

启动前先确认无其他脚本在跑（后台长跑 PID 文件不存在）。后台启动并重定向日志
（启动命令立即返回，向用户汇报"闯关已启动"，**不等待结束**）：

```text
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "<启动器路径>"
```

启动器为只含一条 `Start-Process` 的 .ps1（内容模板如下，路径按机器展开；本机已
生成于 `local/launch_battle.ps1`）：

```text
Start-Process -FilePath "<PYTHON>" -ArgumentList '"<SKILL_DIR>/scripts/battle_run.py"' -WindowStyle Hidden -RedirectStandardOutput "$env:TEMP\fkssj_battle_run.log" -RedirectStandardError "$env:TEMP\fkssj_battle_run.err.log"
```

> **Hermes 终端坑（各机同此，勿再尝试 nohup）**：`nohup` / `disown` / `setsid`
> 会被 Hermes 终端工具直接拒绝（"Foreground command uses shell-level background
> wrappers"），命令根本不执行；`background=true` 又会把进程绑在调用会话上，长跑
> 中途会话结束即被杀。后台长跑**一律用上面的 PowerShell 分离启动器**（实测进程
> 独立存活、调用立即返回）。
>
> **启动器 .ps1 必须纯 ASCII（中文注释会静默失效）**：PowerShell 5.1 读取**无 BOM**
> 的 .ps1 时按 ANSI/GBK 解码，文件里任何非 ASCII 字节（如中文注释）都会破坏解析。
> 症状极具欺骗性：`powershell.exe -File <启动器>` **退出码 0、终端无任何输出**，
> `Start-Process` 根本没执行——PID 文件不出现、日志文件不被截断/不更新（还是上一轮
> 的旧内容），容易误判成"脚本秒退"。2026-10-17 实测：带中文注释的启动器静默失败，
> 删掉非 ASCII 后立即正常。**启动器注释一律用英文或干脆不写**；写完用
> `grep -nP '[^\x00-\x7F]' <启动器>` 确认无非 ASCII 字节
> （返回 1 = 干净），必要时用 PowerShell `Parser::ParseFile` 做语法校验。

启动后验证与汇报（拉起即走，不等结果）：

1. 启动命令返回后等待约 5 秒，确认 `$TEMP/fkssj_battle.pid` 存在；
2. 存在 → 向用户汇报"闯关已启动"（结束后脚本自动推送战果：日间直推微信、
   夜间写夜间日志；让位/停止场景由 agent 推送，见下文）；
3. 不存在 → 启动失败：`tail -n 10 "$TEMP/fkssj_battle_run.log"`
   （err.log 非空时也取其尾部），按输出规范汇报启动失败。
   若日志仍是**上一轮的旧内容且时间戳没更新**（不是新启动的失败日志），先按上文
   检查启动器是否含非 ASCII 字节——这是"什么都没发生"的最常见原因。

- **严禁前台等待**：battle_run 无固定时长，前台等待必然导致调用会话超时。
- 启动前查 `$TEMP/fkssj_battle.pid`，存在即视为在跑，不得重复启动。
- 本机部署存在 `local/commands.md` 时直接用其中现成的后台启动完整命令。

## 停止与战果汇报

用户说"停止闯关 / 别打了"：

```text
<PYTHON> <SKILL_DIR>/scripts/battle_run.py --stop
```

停止后取后台日志尾部统计汇报：

```text
tail -n 15 "$TEMP/fkssj_battle_run.log"
```

按输出规范三字段格式汇报（闯关战果：胜/负/用时），"结果"字段含其 RESULT 行。

**推送战果后必须删除战果标记**（`--stop` 强杀不走脚本自推；该标记同时是日间
直推失败的兜底信号，推送后删除防检查类任务兜底重复推送）：

```text
rm -f "$TEMP/fkssj_battle_done.pending"
```

若 `--stop` 返回"闯关未在运行"但 `$TEMP/fkssj_battle_done.pending` 存在，说明有一场
未推送的旧战果：同样取日志尾部推送并删除该标记，并向用户说明闯关刚才已不在运行。

## 让位规则（闯关与其他任务冲突时，唯一定义）

**其他任务永远优先于后台闯关**（用户单次脚本与定时检查任务同此规则）：

1. 冲突时先运行 `battle_run.py --stop` 停止闯关；
2. 用 `tail -n 15 "$TEMP/fkssj_battle_run.log"` 取战果汇报给用户，
   随后 `rm -f "$TEMP/fkssj_battle_done.pending"`
   清除战果标记（闯关被 --stop 强杀不走脚本自推，战果由让位方推送）；
3. 再执行该任务。

- 夜间 01:00:00-07:59:59 战果不推送，但停止闯关的步骤仍要执行：改为把战果摘要
  记入夜间日志后删除标记——
  `echo "[<当前MM-DD HH:MM>] 闯关: <战果摘要>" >> "$TEMP/fkssj_night_events.log"`
  （留待 08:04 夜间总结推送任务统一推送）。
- 让位后该任务正常进行；任务结束后用户想继续闯关，需再次说"闯关"启动。

## 结果自动推送（v3.0.0：退出路径自推 + 标记兜底）

`battle_run.py` 启动写 PID 时自动创建标记 `$TEMP/fkssj_battle_done.pending`。
脚本**任何正常退出路径**（连败/超时告警、用户中断、异常）在 finally 中自动推送
战果（结束即推，秒级送达，不再依赖 cron 轮询）：

- **夜间**（01:00:00-07:59:59）：只写夜间日志 `$TEMP/fkssj_night_events.log`
  （行格式 `[MM-DD HH:MM] 闯关: 摘要`），由每天 08:04 的夜间总结推送任务统一
  总结推送；
- **日间**：经 `game_lib.push_weixin()` 直推微信（内置 30 秒推送锁，与其余
  直推通道互斥），推送成功。失败自动短时重试（默认共 3 次，间隔由推送锁自然
  拉开约 30 秒），每次尝试（成功/失败+原因）追加一行到 `$TEMP/fkssj_push.log`。

推送成功或已记夜间日志后自动删除标记；**日间 3 次尝试全败则保留标记**——标记存在
语义降级为"有未送达的闯关战果，等待兜底"：

- **兜底链**（顺路补推后删标记）：检查类任务 prompt 步骤 6 → 夜间总结推送任务
  步骤 4 → agent 收到用户查询时（见上文停止与战果汇报的旧战果处理）；
- **让位/主动停止**：`--stop` 走 taskkill /F 强杀不进 finally，无自推——战果由
  让位方/agent 推送（夜间记入夜间日志）后删标记；
- **幂等规则**：任何向用户推送闯关最终战果（或写入夜间日志）的动作之后都必须
  删除该标记；标记不存在即视为已处理，不再重复。

## 严禁与后台闯关并行

- **与后台闯关并行跑其他脚本**（如在 battle_run 运行中直接跑 gather_res）：adb
  点击流互相干扰，会造成误点、采集计秒被打断、退出失败误报。正确做法：先
  `battle_run.py --stop` 停止闯关并取日志尾部战果汇报，再执行其他任务。
- **force_main.py 运行前先确认无后台长跑在跑**：它重启游戏，会掐断任何在途操作。
