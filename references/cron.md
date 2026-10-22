# 定时任务与提醒（/cron 编排 + 系统计划任务，唯一权威）

> **职责**：管理本 skill 的推送/提醒设施——6 个 Hermes /cron 定时任务（贸易/资源
> 检查、城战奖励领取、经验与联盟情报领取、夜间总结推送、每日服务总结）、1 个 Windows 计划任务
> （货轮/商船到点提醒，schtasks 整点唤醒 `scripts/push_reminder.py`）、
> 1 个常驻后台进程（私聊未读监视 `scripts/chat_watch.py`）；后两者的注册/
> 启动/停止见 `references/chat.md`。
> **何时读取**：用户说"开启/关闭 + 任务名"、"提醒货轮/商船"、"每日服务总结"，
> 或想盘点当前开了哪些任务/监控时。

## 开启/关闭规则

用户说"开启/关闭 + 任务名"时：

- /cron 任务（贸易/资源/领取/夜间总结推送）：先 `/cron list` 查重，同类任务已存在
  则告知用户、不重复创建；不存在则用 `/cron add "<cron 表达式>" "<任务 prompt>"`
  创建。关闭：`/cron list` 找到对应任务（prompt 首行含【fkssj …】标识）后删除。
- 货轮/商船提醒（Windows 计划任务）：注册/删除命令见 `references/chat.md`。
- 私聊监视（常驻进程）：启动/停止命令见 `references/chat.md`。
- 用户说"暂停自动化 / 我想自己玩一会 / 恢复自动化" → 一键暂停/恢复协议（暂停
  会删除当时全部【fkssj …】任务并记录状态文件，恢复按清单重建）见
  `references/pause.md`。
- 用户指定检查周期（如"每 1 小时"）→ 换算成对应 cron 表达式；
  提醒类任务是游戏刷新时间，固定不可改。

## 任务表

| 任务 | 开启触发词 | 默认 cron 表达式 | 关闭触发词 |
|---|---|---|---|
| 自动检查贸易 | "开启自动检查贸易" | `*/30 * * * *` | "关闭自动检查贸易" |
| 自动检查资源 | "开启自动检查资源" | `5,35 * * * *` | "关闭自动检查资源" |
| 自动领取城战在线奖励 | "开启自动领取城战在线奖励" | `25 20 * * *` | "关闭自动领取城战在线奖励" |
| 自动领取经验与联盟情报 | "开启自动领取经验"或"开启自动领取联盟情报" | `50 0,8,16 * * *` | "关闭自动领取经验"或"关闭自动领取联盟情报" |
| 夜间总结推送 | "开启夜间总结推送" | `4 8 * * *` | "关闭夜间总结推送" |
| 每日服务总结 | "开启每日服务总结" | `4 1 * * *` | "关闭每日服务总结" |

**v3.0.0 起不再存在的 /cron 任务（勿按旧文档重建）**：

- 搁浅的货轮提醒 / 联盟商船提醒 → 迁移为 Windows 计划任务整点唤醒
  `scripts/push_reminder.py` 直推（0 token），见 `references/chat.md`；
- 长跑结果推送 → 长跑脚本（battle_run.py / claim_seq.py）退出路径自推
  （结束即推、夜间写夜间日志）；`*_done.pending` 标记降级为"日间直推失败的
  兜底"，由检查类任务与夜间总结推送任务顺路补推。

领取任务取 20:25 的理由：奖励仅每天 20:00-21:00 可领；20:00 贸易、20:05 资源
检查最坏情况（3 组全部触发采集 + 统一复查）约 18 分钟、20:23 前必然结束，序列
20:25 启动、约 20:47 完成，仍在领取窗口内。领取序列与其余任务的冲突规则见
`references/reward.md`。

夜间总结推送取 08:04 的理由：夜间窗口结束的 08:00 整点 push_reminder 会推送
货轮提醒，夜间总结刻意错开 4 分钟，避免同刻互挤（见"微信推送节流"）。

## 任务 prompt 模板

`/cron add` 第二参数照抄；命令必须写完整路径——执行会话没有当前对话上下文，
短名脚本无法定位。本机部署存在 `local/commands.md` 时直接用其中的完整路径版
prompt（`local/commands.md` 优先规则见母 SKILL.md"运行位置"节）；其他部署把
`<PYTHON>`/`<SKILL_DIR>` 替换为实际安装路径。prompt 自包含：夜间规则（夜间
不推送、写夜间日志）、正常轮静默（日间一切正常不汇报，异常或采集/交货动作才
推送，v3.2.3）、闯关让位步骤、长跑标记兜底补推步骤、领取序列跳过/防重复/
窗口守卫步骤、闯关挂机奖励顺路领取步骤（仅贸易模板）、游戏未运行询问步骤均已内置，逐字照抄即可。夜间日志行格式统一为
`[MM-DD HH:MM] 任务名: 摘要`（时间取当前时刻，任务名固定用：闯关 / 城战奖励 /
贸易 / 资源 / 经验 / 情报 / 私聊）。

自动检查贸易：

```text
【fkssj 自动检查贸易】依次执行:
1. 若闯关在后台运行(存在 $TEMP/fkssj_battle.pid), 先运行
   <PYTHON> <SKILL_DIR>/scripts/battle_run.py --stop,
   再用 tail -n 15 "$TEMP/fkssj_battle_run.log" 取闯关战果,
   推送战果给用户后运行 rm -f "$TEMP/fkssj_battle_done.pending"
   (闯关脚本正常结束会自己推送战果并删标记, 走到这一步说明是被本轮让位停止的;
   若当前时间在 01:00:00-07:59:59 之间, 战果不推送, 改为记入夜间日志:
   echo "[<当前MM-DD HH:MM>] 闯关: <战果摘要>" >> "$TEMP/fkssj_night_events.log",
   记完后同样 rm -f 删除该标记, 留待早上夜间总结推送任务统一推送)
2. 若领取序列在后台运行(存在 $TEMP/fkssj_claim_seq.pid), 本轮直接跳过:
   不等待、不停止、不执行任何检查, 结束本轮(下一轮自动补上)
3. 运行 <PYTHON> <SKILL_DIR>/scripts/game_status.py 只读探测游戏状态:
   - RESULT 为"游戏运行中": 继续下一步
   - RESULT 为"模拟器未启动"或"模拟器已启动 游戏未运行":
     若当前时间在 01:00:00-07:59:59 之间, 不询问用户, 本轮直接跳过(不启动游戏), 结束;
     否则询问用户"游戏未运行, 是否现在启动游戏并执行本轮检查? (3分钟内未回复视为不同意)"并等待回复:
     · 用户同意: 若模拟器未启动, 先运行雷电模拟器启动命令
       <雷电安装目录>/ldconsole.exe launch --index 0
       (路径按本机安装位置展开, 存在 local/commands.md 时优先用其中现成命令), 等待约90秒;
       再运行 <PYTHON> <SKILL_DIR>/scripts/start_game.py 启动游戏并等其停主界面,
       成功后继续下一步, 失败则按输出规范汇报启动失败并结束本轮
     · 用户不同意或3分钟内未回复: 不启动游戏, 跳过本轮, 结束
   - RESULT 为"检测异常": 按输出规范汇报异常, 结束本轮
4. <PYTHON> <SKILL_DIR>/scripts/check_main.py
5. <PYTHON> <SKILL_DIR>/scripts/check_ships.py
6. <PYTHON> <SKILL_DIR>/scripts/claim_battle_reward.py (顺路领取闯关挂机奖励:
   清升级点 -> OCR 挂机小时与上限 -> 小时 >= 上限-1 或 >= 23 才领取,
   未达条件自动跳过并回主界面)
汇报规则(日间条件推送, v3.2.3): 若本轮一切正常(check_ships RESULT 无"交货失败"/"异常"
字样, 且 claim_battle_reward RESULT 为"闯关奖励未领取 挂机时长不足"), 属正常轮——
不汇报, 夜间日志与每日统计照记后**最终响应只输出 [SILENT]**(Hermes
cron 的静默标记, 逐字输出英文、勿写成 [静默] 等任何变体, 平台据此跳过微信投递);
否则把
check_ships.py 与 claim_battle_reward.py 的 RESULT 行原样汇报给用户。
若当前时间在 01:00:00-07:59:59 之间,
只执行检查不推送, 并把 RESULT 摘要记入夜间日志:
echo "[<当前MM-DD HH:MM>] 贸易: <RESULT 摘要>" >> "$TEMP/fkssj_night_events.log"
(留待早上夜间总结推送任务统一推送)
然后无论日间夜间, 都追加一行每日统计(供 01:04 每日服务总结任务计数):
echo "[<当前MM-DD HH:MM>] 贸易: 完成1轮检查(<RESULT 摘要>)" >> "$TEMP/fkssj_stats.log"
7. 战果兜底补推: 若 $TEMP/fkssj_battle_done.pending 存在(闯关结束日间直推失败的
   降级标记), 用 tail -n 15 "$TEMP/fkssj_battle_run.log" 取战果按输出规范推送给用户,
   然后 rm -f "$TEMP/fkssj_battle_done.pending"; 若 $TEMP/fkssj_claim_seq_done.pending
   存在(领取序列同理), 用 tail -n 15 "$TEMP/fkssj_claim_seq.log" 取结果补推后同样删标记。
   夜间窗口内不推送: 把摘要记入夜间日志(任务名"闯关"/"城战奖励")后删除对应标记
静默总则: 夜间窗口内本轮所有结果只写夜间日志, 执行完全部步骤后**最终响应只输出
[SILENT]**(Hermes cron 的静默标记, 平台据此跳过微信投递)——必须逐字输出英文
[SILENT], 勿写成 [静默] 等任何变体或其它文字(2026-10-19 05:35 泄漏教训: 该轮
把标记写成了中文 [静默], 平台不识别、当作正常汇报投递到微信); 日间仅异常轮
汇报(见第 5 步汇报规则), 正常轮同样只输出 [SILENT]
```

自动检查资源：

```text
【fkssj 自动检查资源】依次执行:
1. 若闯关在后台运行(存在 $TEMP/fkssj_battle.pid), 先运行
   <PYTHON> <SKILL_DIR>/scripts/battle_run.py --stop,
   再用 tail -n 15 "$TEMP/fkssj_battle_run.log" 取闯关战果,
   推送战果给用户后运行 rm -f "$TEMP/fkssj_battle_done.pending"
   (闯关脚本正常结束会自己推送战果并删标记, 走到这一步说明是被本轮让位停止的;
   若当前时间在 01:00:00-07:59:59 之间, 战果不推送, 改为记入夜间日志:
   echo "[<当前MM-DD HH:MM>] 闯关: <战果摘要>" >> "$TEMP/fkssj_night_events.log",
   记完后同样 rm -f 删除该标记, 留待早上夜间总结推送任务统一推送)
2. 若领取序列在后台运行(存在 $TEMP/fkssj_claim_seq.pid), 本轮直接跳过:
   不等待、不停止、不执行任何检查, 结束本轮(下一轮自动补上)
3. 运行 <PYTHON> <SKILL_DIR>/scripts/game_status.py 只读探测游戏状态:
   - RESULT 为"游戏运行中": 继续下一步
   - RESULT 为"模拟器未启动"或"模拟器已启动 游戏未运行":
     若当前时间在 01:00:00-07:59:59 之间, 不询问用户, 本轮直接跳过(不启动游戏), 结束;
     否则询问用户"游戏未运行, 是否现在启动游戏并执行本轮检查? (3分钟内未回复视为不同意)"并等待回复:
     · 用户同意: 若模拟器未启动, 先运行雷电模拟器启动命令
       <雷电安装目录>/ldconsole.exe launch --index 0
       (路径按本机安装位置展开, 存在 local/commands.md 时优先用其中现成命令), 等待约90秒;
       再运行 <PYTHON> <SKILL_DIR>/scripts/start_game.py 启动游戏并等其停主界面,
       成功后继续下一步, 失败则按输出规范汇报启动失败并结束本轮
     · 用户不同意或3分钟内未回复: 不启动游戏, 跳过本轮, 结束
   - RESULT 为"检测异常": 按输出规范汇报异常, 结束本轮
4. 运行 <PYTHON> <SKILL_DIR>/scripts/check_main.py
5. 运行 <PYTHON> <SKILL_DIR>/scripts/check_res.py。若其 RESULT 行的"不足"列表非空:
   按 [鱼] [塑料,木材,碎布] [废金属,玻璃,海藻] 分组, 每组只采组内剩余最少的一种
   (运行 <PYTHON> <SKILL_DIR>/scripts/gather_res.py 并传资源名参数, 连续采集加
   --no-recheck), 全部采完统一再跑一次 <PYTHON> <SKILL_DIR>/scripts/check_res.py 复查
汇报规则(日间条件推送, v3.2.3): 若本轮 check_res"不足"列表为空且未执行任何采集,
属正常轮——不汇报, **最终响应只输出 [SILENT]**(Hermes cron 的静默标记, 逐字输出
英文、勿写成 [静默] 等任何变体, 平台据此跳过微信投递); 否则把检查与采集结果汇报给用户。
若当前时间在 01:00:00-07:59:59 之间,
只执行不推送, 并把结果摘要记入夜间日志:
echo "[<当前MM-DD HH:MM>] 资源: <检查与采集结果摘要>" >> "$TEMP/fkssj_night_events.log"
(留待早上夜间总结推送任务统一推送)
然后无论日间夜间, 都追加一行每日统计(供 01:04 每日服务总结任务计数):
echo "[<当前MM-DD HH:MM>] 资源: 完成1轮检查(<结果摘要>)" >> "$TEMP/fkssj_stats.log"
6. 战果兜底补推: 若 $TEMP/fkssj_battle_done.pending 存在(闯关结束日间直推失败的
   降级标记), 用 tail -n 15 "$TEMP/fkssj_battle_run.log" 取战果按输出规范推送给用户,
   然后 rm -f "$TEMP/fkssj_battle_done.pending"; 若 $TEMP/fkssj_claim_seq_done.pending
   存在(领取序列同理), 用 tail -n 15 "$TEMP/fkssj_claim_seq.log" 取结果补推后同样删标记。
   夜间窗口内不推送: 把摘要记入夜间日志(任务名"闯关"/"城战奖励")后删除对应标记
静默总则: 夜间窗口内本轮所有结果只写夜间日志, 执行完全部步骤后**最终响应只输出
[SILENT]**(Hermes cron 的静默标记, 平台据此跳过微信投递)——必须逐字输出英文
[SILENT], 勿写成 [静默] 等任何变体或其它文字(2026-10-19 05:35 泄漏教训: 该轮
把标记写成了中文 [静默], 平台不识别、当作正常汇报投递到微信); 日间仅异常轮
汇报(见第 5 步汇报规则), 正常轮同样只输出 [SILENT]
```

自动领取城战在线奖励：

```text
【fkssj 城战在线奖励】依次执行以下步骤:
0. 若闯关在后台运行(存在 $TEMP/fkssj_battle.pid), 先运行
   <PYTHON> <SKILL_DIR>/scripts/battle_run.py --stop,
   再用 tail -n 15 "$TEMP/fkssj_battle_run.log" 取闯关战果汇报给用户,
   推送后运行 rm -f "$TEMP/fkssj_battle_done.pending"
   (闯关脚本正常结束会自己推送战果并删标记, 走到这一步说明是被本轮让位停止的)
1. 运行 <PYTHON> <SKILL_DIR>/scripts/game_status.py 只读探测游戏状态:
   - RESULT 为"游戏运行中": 继续下一步
   - RESULT 为"模拟器未启动"或"模拟器已启动 游戏未运行":
     询问用户"游戏未运行, 是否现在启动游戏并领取奖励? (3分钟内未回复视为不同意)"并等待回复:
     · 用户同意: 若模拟器未启动, 先运行雷电模拟器启动命令
       <雷电安装目录>/ldconsole.exe launch --index 0
       (路径按本机安装位置展开, 存在 local/commands.md 时优先用其中现成命令), 等待约90秒;
       再运行 <PYTHON> <SKILL_DIR>/scripts/start_game.py 启动游戏并等其停主界面,
       成功后继续下一步, 失败则按输出规范汇报启动失败并结束本轮
     · 用户不同意或3分钟内未回复: 不启动游戏, 跳过本轮, 结束
   - RESULT 为"检测异常": 按输出规范汇报异常, 结束本轮
2. 运行 <PYTHON> <SKILL_DIR>/scripts/check_main.py 确认在主界面
3. 若领取序列已在后台运行(存在 $TEMP/fkssj_claim_seq.pid), 不重复启动,
   直接汇报"城战在线奖励序列已在进行"并结束
4. 若当前时间晚于 20:35, 不启动序列,
   直接汇报"已错过今日领取窗口(20:00-21:00)"并结束
5. 启动领取序列(后台, 立即返回, 不等待完成):
   powershell.exe -NoProfile -ExecutionPolicy Bypass -File "<启动器路径>"
   (启动器为只含 Start-Process 的 .ps1, 内部调 claim_seq.py 并把日志写到
   $TEMP/fkssj_claim_seq.log 与 .err.log; 本机现成路径见 local/commands.md,
   没有则按 references/battle.md 的启动器模板先生成;
   不得用 nohup——Hermes 终端会拒绝 shell 级后台包装, 命令不会执行)
6. 等待约5秒后确认 $TEMP/fkssj_claim_seq.pid 存在: 存在则立即向用户汇报
   "城战在线奖励领取已启动(约22分钟共7次), 结束后会自动推送领取结果";
   不存在则 tail -n 10 "$TEMP/fkssj_claim_seq.log"
   (err.log 非空时也取其尾部), 按输出规范汇报启动失败
```

（领取任务固定 20:25 触发，永不落在夜间窗口，探测步骤不写夜间分支；步骤 4 为
领取窗口守卫，详见 `references/reward.md`。）

自动领取经验与联盟情报：

```text
【fkssj 自动领取经验与联盟情报】依次执行:
1. 若闯关在后台运行(存在 $TEMP/fkssj_battle.pid), 先运行
   <PYTHON> <SKILL_DIR>/scripts/battle_run.py --stop,
   再用 tail -n 15 "$TEMP/fkssj_battle_run.log" 取闯关战果,
   推送战果给用户后运行 rm -f "$TEMP/fkssj_battle_done.pending"
   (闯关脚本正常结束会自己推送战果并删标记, 走到这一步说明是被本轮让位停止的;
   若当前时间在 01:00:00-07:59:59 之间, 战果不推送, 改为记入夜间日志:
   echo "[<当前MM-DD HH:MM>] 闯关: <战果摘要>" >> "$TEMP/fkssj_night_events.log",
   记完后同样 rm -f 删除该标记, 留待早上夜间总结推送任务统一推送)
2. 若领取序列在后台运行(存在 $TEMP/fkssj_claim_seq.pid), 本轮直接跳过:
   不等待、不停止、不领取, 结束本轮(领取序列仅 20:25-20:47 运行, 与本任务
   0:50/8:50/16:50 正常不撞; 真撞上时本轮放弃, 用户可稍后当面说"领取经验"或
   "领取联盟情报"补领)
3. 运行 <PYTHON> <SKILL_DIR>/scripts/game_status.py 只读探测游戏状态:
   - RESULT 为"游戏运行中": 继续下一步
   - RESULT 为"模拟器未启动"或"模拟器已启动 游戏未运行":
     若当前时间在 01:00:00-07:59:59 之间, 不询问用户, 本轮直接跳过(不启动游戏), 结束;
     否则询问用户"游戏未运行, 是否现在启动游戏并执行本轮领取? (3分钟内未回复视为不同意)"并等待回复:
     · 用户同意: 若模拟器未启动, 先运行雷电模拟器启动命令
       <雷电安装目录>/ldconsole.exe launch --index 0
       (路径按本机安装位置展开, 存在 local/commands.md 时优先用其中现成命令), 等待约90秒;
       再运行 <PYTHON> <SKILL_DIR>/scripts/start_game.py 启动游戏并等其停主界面,
       成功后继续下一步, 失败则按输出规范汇报启动失败并结束本轮
     · 用户不同意或3分钟内未回复: 不启动游戏, 跳过本轮, 结束
   - RESULT 为"检测异常": 按输出规范汇报异常, 结束本轮
4. 运行 <PYTHON> <SKILL_DIR>/scripts/claim_exp.py (自带主界面校验与自动恢复,
   统一领取训练营/冶炼厂/海兽训练营等各建筑累积经验)
5. 运行 <PYTHON> <SKILL_DIR>/scripts/claim_intel.py (自带主界面校验与自动恢复,
   循环一键领取联盟情报直到不可领; 有等级提升会先过等级提升/结算界面再继续)
汇报规则(日间条件推送, v3.2.7): 两个脚本都执行完后, 若 claim_exp RESULT 为"无经验
可领"且 claim_intel RESULT 为"联盟情报领取完成"(不带等级提升字样), 属正常轮——
不汇报, 每日统计照记后**最终响应只输出 [SILENT]**(Hermes cron 的静默标记, 逐字
输出英文、勿写成 [静默] 等任何变体, 平台据此跳过微信投递); 否则把两个脚本的
RESULT 原样一并列出汇报给用户(经验领取成功有领取动作, 照常推送; 情报等级提升属
特殊情况需用户知晓; 无情报可领说明该轮空转, 提醒用户情报源可能已断); 任一脚本
exit 1 按输出规范汇报异常。若当前时间在 01:00:00-07:59:59 之间, 只执行不推送,
并把两份 RESULT 摘要分别记入夜间日志:
echo "[<当前MM-DD HH:MM>] 经验: <RESULT 摘要>" >> "$TEMP/fkssj_night_events.log"
echo "[<当前MM-DD HH:MM>] 情报: <RESULT 摘要>" >> "$TEMP/fkssj_night_events.log"
(留待早上夜间总结推送任务统一推送)
然后无论日间夜间, 都追加两行每日统计(供 01:04 每日服务总结任务计数):
echo "[<当前MM-DD HH:MM>] 经验: 完成1次领取(<RESULT 摘要>)" >> "$TEMP/fkssj_stats.log"
echo "[<当前MM-DD HH:MM>] 情报: 完成1次领取(<RESULT 摘要>)" >> "$TEMP/fkssj_stats.log"
6. 战果兜底补推: 若 $TEMP/fkssj_battle_done.pending 存在(闯关结束日间直推失败的
   降级标记), 用 tail -n 15 "$TEMP/fkssj_battle_run.log" 取战果按输出规范推送给用户,
   然后 rm -f "$TEMP/fkssj_battle_done.pending"; 若 $TEMP/fkssj_claim_seq_done.pending
   存在(领取序列同理), 用 tail -n 15 "$TEMP/fkssj_claim_seq.log" 取结果补推后同样删标记。
   夜间窗口内不推送: 把摘要记入夜间日志(任务名"闯关"/"城战奖励")后删除对应标记
静默总则: 夜间窗口内本轮所有结果只写夜间日志, 执行完全部步骤后**最终响应只输出
[SILENT]**(Hermes cron 的静默标记, 平台据此跳过微信投递)——必须逐字输出英文
[SILENT], 勿写成 [静默] 等任何变体或其它文字(2026-10-19 05:35 泄漏教训: 该轮
把标记写成了中文 [静默], 平台不识别、当作正常汇报投递到微信); 日间仅经验领取
成功、等级提升、无情报可领或异常轮汇报(见上方汇报规则), 经验无可领且情报领取
完成的正常轮同样只输出 [SILENT]
```

（经验与情报自 v3.2.7 起合并为一个任务、一起开启关闭；0:50/8:50/16:50 均在
日间窗口（0:50 早于 01:00 属日间）；claim_exp 约 20 秒 + claim_intel 约 1 分钟
合计约 2 分钟，分钟位 50 与检查类任务（00/30/5/35 分）错开。）

夜间总结推送：

```text
【fkssj 夜间总结推送】依次执行:
1. 检查 $TEMP/fkssj_night_events.log: 文件不存在或内容为空, 直接结束,
   不向用户输出任何内容
2. 读取日志全部行, 把各项夜间事件(闯关/城战奖励/贸易/资源/经验/情报/私聊)总结成一段
   夜间整体汇报推送给用户(保留各事件的时间与要点, 同类重复事件可合并计数)
3. 推送后清空日志: rm -f "$TEMP/fkssj_night_events.log",
   并追加一行每日统计(供 01:04 每日服务总结任务计数):
   echo "[<当前MM-DD HH:MM>] 夜间总结: 完成1次夜间事件推送" >> "$TEMP/fkssj_stats.log"
4. 战果兜底补推: 若 $TEMP/fkssj_battle_done.pending 存在, 用
   tail -n 15 "$TEMP/fkssj_battle_run.log" 取闯关战果按输出规范补推,
   然后 rm -f "$TEMP/fkssj_battle_done.pending"; 若 $TEMP/fkssj_claim_seq_done.pending
   存在, 用 tail -n 15 "$TEMP/fkssj_claim_seq.log" 取领取结果补推,
   然后 rm -f "$TEMP/fkssj_claim_seq_done.pending"
   (该标记是长跑结束日间直推失败的降级兜底, 此处作最后兜底)
```

每日服务总结：

```text
【fkssj 每日服务总结】依次执行:
(本任务固定 01:04 触发, 夜间窗口 01:00:00-07:59:59 内照常推送, 不写夜间日志)
1. 盘点当前开启的服务:
   - /cron list 查询, 记下当前存在的【fkssj …】任务及各自 cron 表达式
   - schtasks /Query /TN "fkssj_push_reminder" 判断货轮/商船提醒计划任务是否在
   - 若 $TEMP/fkssj_chat_watch.pid 存在, 用
     MSYS_NO_PATHCONV=1 tasklist /FI "PID eq $(cat "$TEMP/fkssj_chat_watch.pid")"
     判断私聊监视进程是否存活(输出含 python=在跑; PID 文件在但进程不在=已挂)
2. 读取 $TEMP/fkssj_stats.log(文件不存在或为空则各服务计 0), 把全部行按
   服务名分组计数(服务名固定: 贸易/资源/城战奖励/经验/情报/闯关/提醒/私聊/夜间总结),
   每个服务记出现次数并保留最近一条摘要
3. 推送每日总结给用户, 每个服务一行: 服务名 + 当前是否开启 + 今日完成 N 次
   (+最近一条摘要); 另附一行后台长跑状态(查 $TEMP/fkssj_battle.pid /
   $TEMP/fkssj_claim_seq.pid, 文件存在=在跑)
4. 推送成功后清空计数: rm -f "$TEMP/fkssj_stats.log"
   (推送失败则保留, 下日总结合并计数)
```

## 规则

- **夜间窗口与夜间日志**：01:00:00-07:59:59 为夜间（0 点属日间照常推送）。夜间
  所有任务只执行、不向用户推送——检查结果、长跑战果、私聊提醒一律改写入
  `$TEMP/fkssj_night_events.log`（行格式 `[MM-DD HH:MM] 任务名: 摘要`，任务名固定
  用：闯关 / 城战奖励 / 贸易 / 资源 / 经验 / 情报 / 私聊）；由每天 08:04 的夜间总结推送任务统一
  总结推送后清空。夜间规则已写进各任务 prompt 与脚本，无需另建夜间任务。
  **例外**（豁免均写进各自任务 prompt 自身）：①每日服务总结（01:04）夜间照常
  推送；②【fkssj 暂停询问】任务昼夜照常询问用户——暂停中用户大概率在手动
  游玩、未入睡（协议见 `references/pause.md`）。
- **长跑结果自推（v3.0.0）**：battle_run.py / claim_seq.py 退出路径自动推送结果
  （结束即推，取代原 cron 轮询任务）；夜间只写夜间日志。`*_done.pending` 标记
  语义变为"日间直推失败的降级兜底"：检查类任务与夜间总结推送任务顺路补推后
  删除；`--stop` 让位场景不走自推（强杀不进 finally），由让位方推送战果后删除。
- **货轮/商船提醒（v3.0.0）**：固定时间盲推送，与游戏实际刷新状态无关；已从
  /cron 任务迁移为 Windows 计划任务（schtasks 每小时整点唤醒
  `scripts/push_reminder.py`，内置货轮 8-22 点、商船 8/11/14/17/20/23 点时刻表，
  同刻合并一条，其余小时静默退出，0 token），注册/删除命令见
  `references/chat.md`。
- **私聊未读监视（v3.0.0）**：`scripts/chat_watch.py` 常驻后台进程（非 cron），
  每 2 分钟一轮（相位对齐偶数分钟 :30 秒），发现未读直推提醒、夜间写夜间日志；与闯关/领取序列
  互斥（检测到其 PID 文件时本轮让位）。用法见 `references/chat.md`。
- **每日服务总结（v3.1.0）**：每天 01:04 推送"当前开了哪些服务 + 各服务今日
  完成次数"，夜间照常推送（夜间窗口例外之一，见上方夜间规则）。
  计数文件 `$TEMP/fkssj_stats.log`（行格式同夜间日志；服务名固定：贸易/资源/
  城战奖励/经验/情报/闯关/提醒/私聊/夜间总结），写入方 = 脚本侧（push_result 长跑自推、
  push_reminder 推送成功、chat_watch 检出未读时）+ prompt 侧（贸易/资源/
  夜间总结各模板的 echo 步骤）；总结推送成功后清空，失败保留到下日合并。
  分钟位 4 与夜间总结 08:04 同相位（不同小时，无互挤）。
- **一键暂停与恢复（v3.2.0）**："暂停自动化 / 我想自己玩一会"会删除当时存在的
  全部【fkssj …】任务、静默货轮/商船提醒（停用清单写 `cargo ship`）、停止私聊
  监视与闯关/领取长跑，并结束正在跑的检查类脚本，状态记入
  `$TEMP/fkssj_pause_state`；"恢复自动化"按该文件逐项还原（闯关除外）。暂停
  满 1 小时未恢复由一次性【fkssj 暂停询问】任务（repeat=1，跑完系统自动收尾）
  主动询问一次。完整协议见 `references/pause.md`。
- 城战在线奖励是 20:25 单次唤醒 + 后台序列内部编排（间隔设计原因与不对称互斥规则
  见 `references/reward.md`）；关闭该任务时若序列仍在后台运行，先运行
  `scripts/claim_seq.py --stop` 再删任务。
- **设备占用自检规则（v3.2.9）**：任务脚本启动自检发现其他占设备脚本进程在跑
  则 exit 2（`RESULT: XX未执行 已有YY进程占用设备`）——**定时任务**遇此不打扰
  用户，按优先级表跳过本轮；**用户单发任务**被挡时向用户说明后问三选一
  （跳过在跑任务轮立即执行 / 等占用结束再执行 / 暂不执行）。
  名单与机制见 `references/scripts.md` 设备占用自检段。
- **闯关让位规则**：定时任务与后台闯关冲突时任务优先——各检查类任务 prompt 已
  内置"先停止闯关并汇报战果"步骤；夜间让位战果写夜间日志不推送。
  完整规则见 `references/battle.md`。
- **领取序列跳过规则**：检查类任务遇 `fkssj_claim_seq.pid` 存在则跳过本轮
  （已内置 prompt 步骤 2），完整规则见 `references/reward.md`。
- **游戏未运行询问规则**：检查类任务与领取任务 prompt 已内置 game_status.py 探测
  步骤——游戏未运行时先询问用户是否启动游戏（3 分钟内未回复视为不同意），同意则
  启动模拟器（`ldconsole launch --index 0`，**勿用 `--name`**：`--name` 要与实例
  显示名完全一致，而显示名各机不同（默认多为"雷电模拟器"，可被改名），不匹配时
  ldconsole 只打印 usage、exit 127、模拟器不启动；`--index 0` 始终指向第一个实例，
  各机通用。ldconsole 完整路径按安装位置展开，存在 `local/commands.md` 时优先用
  其中现成命令）与游戏后继续，否则跳过本轮；夜间 01:00:00-07:59:59 不询问，
  直接跳过本轮。
- **微信推送节流（iLink 30 秒冷却）**：微信 iLink 推送通道每 30 秒只能送达一条，
  30 秒窗口内第二条起会被静默丢弃。v3.0.0 起所有**脚本直推**统一走
  `game_lib.push_weixin()`——函数内置 30 秒推送锁（`$TEMP/fkssj_push_guard` 存上次
  推送 epoch 秒：推送前读锁、不足 30 秒 sleep 补满、写锁后发送），同刻多脚本互挤
  时后到者自动等满，全部送达。2026-10-17 起函数内置短时重试：默认共试 3 次，失败后
  由推送锁自然拉开约 30 秒再试，每次尝试（ok/fail+原因）追加一行到
  `$TEMP/fkssj_push.log`；提醒类 push_reminder 传 max_tries=1、失败后约 40 秒
  外层重试 1 次（2026-10-18 起，避开 iLink 冷却），仍失败不补推、下一整点照常。**agent 会话推送**（让位战果、夜间总结、每日
  服务总结、兜底补推）不经该函数，需靠分钟位错开：夜间总结与每日服务总结均
  取 4 分（不同小时，无互挤）、检查类任务回复前有脚本耗时（分钟
  级）天然错开。全系统错峰格局：货轮/商船 schtasks 整点 0 分、chat_watch tick
  相位 :30 秒（两者走脚本内置锁，无需额外错开）、夜间总结/每日服务总结 4 分。
  新建任务或自
  定义周期时，即时回复任务的分钟位必须与之错开，能错峰的优先错峰。
- **同刻多任务优先级表**（占设备越久优先级越靠后；默认表达式已按此错峰）：
  1. 货轮/商船提醒（push_reminder 纯推送，不占设备）
  2. 夜间总结推送 / 每日服务总结（均只读本地文件与 /cron list，不占设备）
  3. 自动领取经验与联盟情报（合并任务约 2 分钟，分钟位 50）
4. 自动检查贸易（含闯关挂机奖励领取，约 2-4 分钟）
5. 自动检查资源（最坏约 18 分钟）
6. 自动领取城战在线奖励（序列占设备约 22 分钟，永远最后）
7. chat_watch 私聊监视（常驻，tick 相位 :30 秒；遇 3-6 占设备时按 PID 让位跳过本轮）
  用户自定义检查周期时，建任务的 agent 必须按本表把分钟位错开（短任务在前、
  长任务在后）；无法错开时同会话按表序串行执行；让位/跳过规则优先于本表生效。
