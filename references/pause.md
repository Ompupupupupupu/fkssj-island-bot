# 一键暂停与恢复自动化（唯一权威）

> **职责**："暂停自动化 / 我想自己玩一会"一键停掉全部自动化（【fkssj …】/cron
> 定时任务、货轮/商船到点提醒、私聊监视、闯关/领取序列长跑、正在跑的检查类
> 脚本），"恢复自动化"按暂停前状态逐项恢复（闯关除外）；暂停满 1 小时未恢复
> 由一次性询问任务主动询问一次。
> **何时读取**：用户说"暂停自动化 / 我想自己玩一会 / 我要自己玩会儿"或
> "恢复自动化"，或排查暂停、询问、恢复的异常时。

## 范围与不变式

- **暂停的是"自动"，不拦手动**：暂停后用户当面发起的单次脚本（检查贸易、采集
  资源等）照常可用；恢复前所有自动触发（/cron 任务、整点提醒、私聊监视、
  长跑自推）全部停止。
- **状态文件是恢复的唯一依据**：`$TEMP/fkssj_pause_state`。存在 = 暂停中；恢复
  流程读取它逐项还原后删除。文件被外部删除视为"已恢复"——询问任务查不到它
  就不再询问、直接结束（repeat=1 跑完自动收尾）。
- **恢复不重启闯关**（用户约定）：暂停时被停止的闯关不会自动恢复，用户要继续
  闯关需另行说"闯关"。
- **询问任务一次性**：只在暂停时确实有至少一项自动化在开启才创建；创建时指定
  重复次数 1（repeat=1，跑完本轮系统自动收尾），触发后无论用户是否回复都不
  重复询问、不常驻占用 API。任务运行中不得删除自身——cron 对微信的投递发生
  在会话运行结束之后，运行中删除任务会静默吞掉该轮投递（2026-10-18 事故教训）。
- **长跑战果不让位丢失**：暂停停止闯关/领取序列时的战果按让位规则处理（日间
  推送、夜间写夜间日志），处理后删对应 pending 标记。

## 暂停自动化（"暂停自动化" / "我想自己玩一会"）

依次执行（命令路径规则同母 SKILL.md"运行位置"节：本机存在 `local/commands.md`
时优先用其中完整路径命令，下同）：

1. **重复暂停守卫**：`$TEMP/fkssj_pause_state` 已存在 → 当前已在暂停中，向用户
   说明后结束，不重复执行、不重建询问任务。
2. **盘点当前在开的自动化**：
   - `/cron list` 记下当前全部【fkssj …】任务的任务名与 cron 表达式（含夜间
     总结推送、每日服务总结——暂停期间一律停）；
   - 查 `$TEMP/fkssj_battle.pid` / `$TEMP/fkssj_claim_seq.pid` /
     `$TEMP/fkssj_chat_watch.pid` 是否存在（存在=在跑）；
   - `MSYS_NO_PATHCONV=1 schtasks /Query /TN "fkssj_push_reminder"` 判断货轮/
     商船提醒计划任务是否注册；
   - `cat "$TEMP/fkssj_reminder_off"` 记下原内容（报 No such file 记 none）。
   **若四类全为关**（无【fkssj …】任务、三个 PID 全不在、提醒计划任务未注册
   或原清单已 `cargo ship` 全停）→ 当前没有在运行的自动化，向用户说明后结束，
   不写状态文件、不建询问任务。
3. **停止后台长跑与常驻监视**（战果按让位规则处理：日间推送给用户、夜间
   01:00:00-07:59:59 写夜间日志 `$TEMP/fkssj_night_events.log`，处理后删对应
   pending 标记；完整规则见 `references/battle.md` 让位节与
   `references/reward.md`）：
   - 闯关在跑 → `battle_run.py --stop`，`tail -n 15 "$TEMP/fkssj_battle_run.log"`
     取战果处理，`rm -f "$TEMP/fkssj_battle_done.pending"`；
   - 领取序列在跑 → `claim_seq.py --stop`，
     `tail -n 15 "$TEMP/fkssj_claim_seq.log"` 取结果处理，
     `rm -f "$TEMP/fkssj_claim_seq_done.pending"`；
   - 私聊监视在跑 → `chat_watch.py --stop`。
4. **结束正在跑的检查类脚本**（防其继续点击与用户手动游玩互相干扰）：用
   PowerShell CIM 枚举 python 进程命令行（本机 wmic 已移除，各机同此用 CIM）：

   ```text
   powershell.exe -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name LIKE 'python%'\" | Select-Object ProcessId,CommandLine | Format-List"
   ```

   命中占设备脚本名单（check_main / check_ships / check_res / gather_res /
   claim_online_reward / claim_seq / battle_run / start_game / stop_game /
   force_main / status_check，与 chat_watch 让位同款名单）→
   `MSYS_NO_PATHCONV=1 taskkill /PID <该进程PID> /F` 逐个结束，并向用户说明被
   中断的那轮检查/采集恢复后可顺带补做。无命中跳过本步。
5. **静默货轮/商船提醒**：`printf 'cargo ship' > "$TEMP/fkssj_reminder_off"`
   （两类全停；计划任务注册状态不动，恢复时按第 2 步记录还原）。
6. **写暂停状态文件** `$TEMP/fkssj_pause_state`（一行一项；ask_at 先按第 8 步
   规则算出询问时刻再写）：

   ```text
   paused_at: <MM-DD HH:MM>
   battle_was: on|off
   claim_seq_was: on|off
   chat_watch: on|off
   reminder_task: on|off（计划任务注册状态，仅汇报用，恢复不重建）
   reminder_off_prev: <第2步记录的原清单内容或 none>
   tasks: <任务名1>=<表达式1>; <任务名2>=<表达式2>; ...（无任务写 none）
   ask_at: <第8步询问任务的 cron 表达式>
   ```

7. **删除全部【fkssj …】/cron 任务**（含可能残留的旧【fkssj 暂停询问】）。
8. **建 1 小时询问任务**（仅当第 2 步盘到至少一项自动化在开启）：取当前时刻
   +1 小时为询问时刻，**昼夜一律 +1 小时、不顺延**（夜间窗口 01:00:00-07:59:59
   也照常询问：会暂停通常说明用户在手动游玩、大概率未入睡；豁免声明已写进
   prompt 模板首行，不会被夜间静默规则拦下）；`/cron add "<分> <时> * * *"
   "<下述 prompt>" --repeat 1`——必须创建为一次性任务（repeat=1，跑完系统
   自动收尾；若 /cron add 参数形态不同，以使任务 repeat.times=1 的等价方式
   创建）。prompt 首行标识【fkssj 暂停询问】。
9. **汇报**：已暂停各项清单 + "说'恢复自动化'即可恢复（闯关不会自动恢复）" +
   "满 1 小时未恢复会主动询问一次"。

### 询问任务 prompt 模板（/cron add 第二参数照抄，<SKILL_DIR> 按实际安装路径展开）

```text
【fkssj 暂停询问】本任务是"暂停自动化"满 1 小时的一次性主动询问(创建时已指定
repeat=1, 跑完本轮系统自动收尾, 不会每日重复), 昼夜照常执行(不受
01:00:00-07:59:59 夜间静默规则限制; 用户暂停自动化通常在手动游玩, 大概率
未入睡), 依次执行:
1. 检查暂停状态文件(存在=仍在暂停): ls "$TEMP/fkssj_pause_state"
   - 不存在: 用户已恢复自动化, 无需询问, 直接结束
   - 存在: 继续第 2 步
2. 询问用户: "海岛自动化已暂停满 1 小时, 需要恢复吗? 回复'恢复自动化'即可恢复
   (闯关不会自动恢复)", 等待约 3 分钟:
   - 用户明确同意恢复: 读取 <SKILL_DIR>/references/pause.md, 按"恢复自动化"节
     逐步执行(本机存在 local/commands.md 时优先用其中完整路径命令), 但跳过
     恢复流程中"删除询问任务"那一步(本会话即该任务自身, 运行中删除会吞掉
     恢复汇报的投递; repeat=1 会自动收尾), 其余步骤照常, 结束
   - 用户拒绝或未回复: 保持暂停, 结束
警告: 全程不得删除本任务自身——cron 对微信的投递发生在本会话运行结束之后,
运行中删除任务会静默吞掉本轮投递(2026-10-18 事故教训); 一次性已由 repeat=1
在系统层保证, 无需自行删除
```

## 恢复自动化（"恢复自动化"）

依次执行：

1. `$TEMP/fkssj_pause_state` 不存在 → 当前没有暂停中的自动化，向用户说明后结束。
2. 读取状态文件各项。
3. **重建 /cron 任务**：按 tasks 清单逐个创建（表达式用状态文件记录值，保留
   用户自定义周期）；prompt 优先用 `local/commands.md` 的完整路径版，不存在则
   按 `references/cron.md` 模板以实际安装路径展开。建后 `/cron list` 复验。
4. **私聊监视**：chat_watch=on → 按 `references/chat.md` 启动节后台启动
   （background 方式发起，启动后验证 pid 文件与日志新行）；off → 不动。
5. **还原提醒停用清单**：reminder_off_prev=none →
   `rm -f "$TEMP/fkssj_reminder_off"`；否则把原内容写回该文件。
   （计划任务注册状态暂停期间未动，无需处理。）
6. **删除询问任务**（若仍存在）：/cron list 找 prompt 首行含【fkssj 暂停询问】
   的任务后删除。**例外**：本会话若由询问任务自身触发（当前指令来自
   【fkssj 暂停询问】prompt），跳过本步不删——运行中删除自身会吞掉本会话
   恢复汇报的投递；repeat=1 会让它跑完自动收尾。
7. `rm -f "$TEMP/fkssj_pause_state"`。
8. **夜间日志兜底**：若 `$TEMP/fkssj_night_events.log` 存在且非空、且当前时刻
   已过当日 08:04（暂停跨过了夜间总结时刻），把其中事件总结推送一次后清空
   （与夜间总结推送任务同语义，行格式见 `references/cron.md`）。
9. **汇报**：已恢复各项清单 + "闯关未自动恢复（如需要请说'闯关'）"；若暂停
   跨过了 01:04，说明当日每日服务总结已错过、计数并入次日推送
   （`$TEMP/fkssj_stats.log` 保留不清，下日总结合并计数）。

## 排查

- **暂停期间仍有 fkssj 任务触发**：暂停只删除暂停时刻已存在的任务；暂停后用户
  又当面说"开启 X"新建的任务不受影响（属合理）。`/cron list` 里若还有暂停前
  的【fkssj …】残留 = 暂停协议第 7 步漏删，按任务名手动删除即可。
- **满 1 小时没收到询问**：①暂停时没有任何自动化在开（第 2 步提前结束，不建
  询问任务，属正常）；②询问任务在但 Hermes /cron 未运行（会话不触发）→ 用户
  侧核实 /cron 状态；③询问已触发过一次（repeat=1 一次性，跑完自动收尾，
  不重复问）。
- **"恢复自动化"后任务没回来**：状态文件被外部删除（视为已恢复）或重建时
  `local/commands.md` 与 `references/cron.md` 模板口径不一致 → 按当前需求逐个
  "开启 X"重建（commands.md 同步义务见 `references/maintenance.md` 部署节）。
- **电脑重启后**：/cron 任务与 Windows 计划任务不受影响；chat_watch 本就不自启
  （见 `references/chat.md`），恢复流程按状态文件记录处理即可。
