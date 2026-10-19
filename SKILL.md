---
name: fkssj-island-bot
description: "Use when 用户提到 fkssj、海岛经营游戏、fkssj帮助/ssj帮助、游戏启动或停止、贸易船检查或交货、资源检查或采集、闯关或停止闯关、领取城战在线奖励（手动领第x次）、主界面检查或强制恢复、开启或关闭定时任务或提醒（自动检查贸易/自动检查资源/自动领取城战在线奖励/夜间总结推送/每日服务总结/货轮提醒/商船提醒/私聊监视、暂停自动化/我想自己玩一会/恢复自动化）。本 skill 通过雷电模拟器的 adb server (127.0.0.1:5037) 驱动游戏 com.gx.sw.qa.fkssj003.esj，提供单次执行的自动化脚本：模拟器平板版配置检查修正、启动/停止游戏、检查并恢复主界面、三船贸易检查+自动交货、7 种资源 OCR 检查、单资源采集（时长按剩余百分比自动定 1/3/5 分钟，采后自动复查全部资源，多资源用 --no-recheck 分组编排）、强制重启回主界面、城战在线奖励单次领取（第 1-7 次任一次）与 7 次序列后台领取、自动闯关（后台运行、--stop 停止）；长任务一律后台启动防会话超时。推送架构：长跑脚本（闯关/领取序列）退出路径自动直推微信战果（夜间写夜间日志）、货轮/商船到点提醒由 Windows 计划任务整点唤醒脚本直推（0 token）、私聊未读监视常驻后台进程每 2 分钟检测发现未读直推提醒（脚本直推均内置 30 秒推送锁；夜间事件一律记入夜间日志），并支持用 /cron 编排定时任务：自动检查贸易/资源（默认每 30 分钟可指定周期，夜间 01:00:00-07:59:59 只执行不推送、结果记入夜间日志，资源不足自动采集）、自动领取城战在线奖励（每天 20:25 唤醒一次，后台序列领完 7 次，奖励仅 20:00-21:00 可领）、夜间总结推送（每天 08:04 把夜间日志统一总结推送一次并清空）、每日服务总结（每天 01:04 盘点当前开启的服务与各服务当日完成次数，夜间照常直推）。支持一键暂停/恢复全部自动化（暂停即停定时任务/到点提醒/私聊监视/后台长跑，满 1 小时未恢复主动询问一次；恢复按暂停前状态逐项恢复，闯关除外）。定时任务遇游戏未运行会先询问用户是否启动（3 分钟无回复跳过本轮）。脚本检查与操作分离，输出 RESULT 汇总行与语义化 exit code。"
version: 3.2.4
author: "Ompupupupupupu"
license: AGPL-3.0
platforms: [windows]
metadata:
  hermes:
    tags: [fkssj, game-automation, adb, ldplayer, ocr, trade-ships, resource-gathering, battle-loop, citywar-online-reward]
    category: automation
    related_skills: [android-device-automation]
---

# fkssj 海岛经营游戏自动化（单次脚本工具包）

## Overview

雷电模拟器 9（`emulator-5554`）中海岛经营游戏 `com.gx.sw.qa.fkssj003.esj`
的自动化脚本集。**环境要求：雷电平板版预设**（1920×1080 + DPI 280，详见"前提条件"）。
设计原则：**单次执行、检查与操作分离、结果可解析**——每个脚本跑一轮
就退出，stdout 末行输出机器可解析的 `RESULT:` 汇总，exit code 表达语义（0 正常 /
1 失败 / 2 需要用户行动）。例外：`battle_run.py` / `claim_seq.py` 是后台长跑
（必须后台启动、`--stop` 停止，防调用会话超时）；`chat_watch.py` 是常驻后台监视
进程（同 `--stop` 模式），`push_reminder.py` 由 Windows 计划任务整点唤醒即退；
其余脚本一律单次执行。

脚本通过本机 adb server（127.0.0.1:5037，雷电模拟器启动后自动在跑）直连设备，
无需 adb.exe 在 PATH。屏幕感知 = 截图 + 模板匹配 + 固定像素颜色判定 + RapidOCR。

各功能操作细节不在本文件展开——见下文"按需读取导航"，按需读取 `references/`
对应文件。

## When to Use

- 用户说"检查模拟器配置 / 分辨率不对 / 平板版设置" → `scripts/setup_emulator.py`（检查+自动修正）
- 用户说"游戏开了吗 / 游戏在运行吗" → `scripts/game_status.py`（只读探测：模拟器未启动 / 游戏未运行 / 游戏运行中）
- 用户说"启动游戏 / 打开游戏" → `scripts/start_game.py`（已运行则报告状态不重启）
- 用户说"停止游戏 / 关掉游戏" → `scripts/stop_game.py`
- 用户说"检查贸易 / 船回来了吗 / 交货" → `scripts/check_ships.py`（检查+自动交货一体）
- 用户说"看看资源 / 鱼够不够 / 木材还剩多少" → `scripts/check_res.py`（只读 OCR）
- 用户说"采集鱼 / 去钓鱼 / 收集海藻" → `scripts/gather_res.py`（时长按剩余百分比自动定 1/3/5 分钟，完成后自动复查全部资源）
- 需要采集多种资源 → 按"典型编排 - 多资源采集"的分组规则决定采哪些：每组只采组内剩余最少一种
- 用户说"闯关 / 打关卡 / 继续打" → 后台启动 `scripts/battle_run.py`，启动后立即汇报（流程见 `references/battle.md`）
- 用户说"停止闯关 / 别打了" → `scripts/battle_run.py --stop`，再取日志尾部统计汇报（见 `references/battle.md`）
- 用户说"领取城战在线奖励 / 帮我领取第x次奖励"（如"帮我领取一下第三次奖励"）→ `scripts/claim_online_reward.py <x>`（手动单次领取，x 为 1-7，见 `references/reward.md`）
- 用户说"回主界面 / 游戏卡在某个界面" → `scripts/check_main.py`，失败再 `scripts/force_main.py`
- 周期性维护 → 编排流程见下文"典型编排"
- 用户说"fkssj帮助 / ssj帮助" → 按 `templates/help.txt` 模板逐行输出树结构功能清单（保持模板换行与缩进）
- 用户说"开启/关闭 + 自动检查贸易 / 自动检查资源 / 自动领取城战在线奖励 / 夜间总结推送 / 每日服务总结" → 用 /cron 创建或删除定时任务（任务表与 prompt 模板见 `references/cron.md`）
- 用户说"开启/关闭 + 货轮提醒 / 商船提醒 / 私聊监视 / 私聊提醒" → 管理货轮/商船 Windows 计划任务或私聊监视常驻进程（见 `references/chat.md`）
- 用户说"暂停自动化 / 我想自己玩一会" → 按暂停协议一键停掉全部自动化（定时任务/提醒/私聊监视/后台长跑，满 1 小时未恢复主动询问一次），见 `references/pause.md`
- 用户说"恢复自动化" → 按恢复协议恢复暂停前开启的服务（闯关除外），见 `references/pause.md`

不适用于：其他游戏、其他分辨率、其他模拟器。

## 按需读取导航（references/）

- 需要某个脚本的参数、exit code、行为细节时 → 读取 `references/scripts.md`
- 用户说闯关/停止闯关，需要闯关战果，或处理闯关与其他任务冲突时 → 读取 `references/battle.md`
- 用户说领取城战在线奖励/帮我领取第 x 次奖励，处理领取序列冲突、关闭自动领取时 → 读取 `references/reward.md`
- 用户说开启/关闭定时任务（自动检查贸易/资源、自动领取城战在线奖励、夜间总结推送、每日服务总结），或想盘点当前开了哪些任务/监控时 → 读取 `references/cron.md`
- 用户说开启/关闭货轮/商船提醒或私聊监视，或排查提醒/监视未推送时 → 读取 `references/chat.md`
- 用户说暂停自动化/我想自己玩一会/恢复自动化，或排查暂停期间异常（暂停后仍有任务在跑、询问没来、恢复后任务没回来）时 → 读取 `references/pause.md`
- 遇到报错、异常现象（连接失败、exit 2、主界面误判），或不确定后台长跑是否在跑时 → 读取 `references/troubleshooting.md`
- 需要修改坐标/颜色常量、校准判定、更新匹配模板，或部署到新机器时 → 读取 `references/maintenance.md`

## 运行位置（强指令）

- **必须从本 skill 的 scripts/ 目录运行脚本**，不得使用其他来源的副本。
- **对模拟器与游戏的一切操作只能经本 skill 的脚本**：截图、点击、滑动、界面
  识别、游戏启停等一律调用 scripts/ 对应脚本完成；**严禁自行构造 adb 命令**
  （如 input tap / input swipe / screencap / shell am 等）或用其他工具直接操作
  设备。唯一例外：任务 prompt 模板中给出的雷电模拟器实例启动命令
  （ldconsole launch --index 0，属电源级操作非游戏内操作）。
- **本 skill 目录对 agent 只读（local/ 除外）**：不得新增、修改或删除 SKILL.md、
  references/、scripts/、templates/、assets/、README.md 等任何 skill 文件；本机
  部署需要的启动器、完整路径命令清单等只写入 local/ 目录。skill 的行为修正与
  功能更新由维护者发布新版本进行，agent 发现缺陷时如实上报用户，勿自行改动
  分发文件。
- **本机部署优先规则**：若本 skill 根目录存在 `local/commands.md`（部署时生成的
  完整路径命令清单），**必须先读取它并逐字使用其中的命令，不得自行改写路径**；
  不存在时按通用模板以实际安装位置展开。
- 通用命令模板（`<PYTHON>` = 已装依赖的 Python 解释器，`<SKILL_DIR>` = 本 skill
  安装根目录）：

```text
<PYTHON> <SKILL_DIR>/scripts/<脚本名>.py
```

- 路径一律用正斜杠原生形式（Git Bash `/c/...` 路径坑见 `references/scripts.md`）。

## 前提条件（缺一不可，先检查再跑）

1. **雷电模拟器 9 已启动**（adb server 随模拟器自动运行）。连接失败报
   `ConnectionRefusedError` / `no devices` = 模拟器没开。
2. **雷电模拟器为平板版预设**：配置分辨率 1920×1080、DPI 280（竖屏显示下 adb 截图
   1080×1920，本 skill 全部坐标基于此）。首次使用或怀疑环境不符时先跑
   `scripts/setup_emulator.py`（非默认安装位置加 `--ld-dir`，多实例加 `--instance`）：
   符合 exit 0；不符自动修正，修正后 exit 2 需重启模拟器生效
   （完整验证链见 `references/scripts.md`）。
3. **Python 3.12+**（已装 `requirements.txt` 中的依赖：opencv-python、
   rapidocr_onnxruntime；实测 3.11 与 rapidocr-onnxruntime 不兼容）。
4. 脚本位于本 skill 的 `scripts/` 目录，匹配模板位于 `assets/`（`assets/nav_stage.png`、
   `assets/btn_fight.png`，脚本按相对路径自动定位，skill 目录整体搬移不影响运行）。
   运行时截图写入 `$TEMP/fkssj_skill_shots/`。
5. **仅支持单模拟器实例**（emulator-5554 / 第一个实例，实例目录 leidian0）；多实例环境请先关闭其他
   实例再运行脚本。

## 输出规范（每次汇报必须遵守）

每次运行脚本后向用户汇报，**必须使用以下统一格式**，所有脚本一致，
不得自由发挥、不得增删字段。**各字段逐行输出，字段之间只换行、不额外空行**
（手机端一页可见优化）：

```text
结果: <脚本输出的 RESULT 行全文；脚本无 RESULT 行时写末行关键状态>
状态: 成功 | 失败 | 需用户行动      (对应 exit code 0 / 1 / 2)
下一步: <按编排流程或恢复链应执行的下一个动作；没有则写"无">
```

**例外（主界面恢复类脚本）**：`check_main.py` / `force_main.py` 运行成功（exit 0）
时，无需输出上述格式，只输出一行：

```text
已回到主界面
```

运行失败（exit 1）时仍按完整格式汇报。

规则：
- **各字段逐行输出，字段之间不额外空行**；字段内的条目列表（资源、动作）同样
  逐行连续排列，条目之间不加空行。
- **长内容必须拆行**：字段值含多个条目时（如 check_res 的 7 种资源）禁止挤在一行，
  必须每个条目单独一行；"下一步"有多个动作时同样每个动作一行。单行能看全的不拆。
- **多步骤用 ↓ 分隔**：连续运行多个脚本/大步骤时，每个步骤单独一块上述格式
  （`已回到主界面` 单行输出也算一块），按执行顺序排列，不要合并；**相邻步骤块之间
  插入一行"↓"（向下箭头独占一行）表示执行推进**（取代空行分隔）；全部步骤汇报完
  可空一行后附一行本轮总结。
- 汇报只保留状态与结果，不要复述 `[HH:MM:SS]` 前缀的过程日志。
- **任何输出不得出现按钮坐标**（本项目硬约定）。
- exit 2 = 需要用户行动（如贸易船缺货、OCR 失败），在"下一步"中写明给用户的建议。
- **长跑脚本特例**：`battle_run.py` / `claim_seq.py` 后台启动后等待约 5 秒确认
  PID 文件存在即报"已启动"、不等待结束（防调用会话超时）；`--stop` 后按其 RESULT
  行汇报——战果推送时机、待推送标记删除、gather_res 的 RESULT 形态等细则见
  `references/battle.md`、`references/reward.md`、`references/scripts.md`。

多条目拆行示例（check_res.py 的 7 种资源与多步采集）：

```text
结果:
上限 12300
鱼 9960 充足
塑料 3720 不足
木材 11500 充足
碎布 9000 充足
废金属 6100 不足
玻璃 11000 充足
海藻 12300 充足
状态: 需用户行动
下一步:
先采集塑料（约3.5分钟）
再采集废金属
```

## 典型编排

**周期维护**（如"帮我做一轮日常"）：`check_main.py` → `check_ships.py` →
`check_res.py` 串行执行（通用命令模板见"运行位置"），汇报按输出规范多步骤 ↓ 分隔。

**多资源采集（分组规则，必须遵守）**：check_res 的 RESULT 行"不足"列表含多种资源时，
按采集界面分组：`[鱼]`、`[塑料, 木材, 碎布]`、`[废金属, 玻璃, 海藻]`。同组的多种资源
不足 → 只采**组内剩余数量最少**的一种；不足资源跨组 → 每组各采一次（各取组内最少）。

- 连续采集时每个 `gather_res.py` 都带 `--no-recheck`，串行执行；**全部采完后统一跑
  一次 `check_res.py` 复查**。只采一种资源时不加 `--no-recheck`（脚本采后自动复查）。

```text
<PYTHON> <SKILL_DIR>/scripts/gather_res.py "鱼" --no-recheck
```

（海藻则把 `"鱼"` 换成 `"海藻"`，或用序号 1-7；单资源场景去掉 `--no-recheck`。）

**恢复链**：`check_main.py` exit 1 → `force_main.py` → 仍 exit 1 才报告用户人工处理
（可能被模态弹窗卡住，不要乱点，如实上报）。

**闯关**：后台启动、停止与战果汇报、让位规则见 `references/battle.md`。

**城战在线奖励**：手动单次领取、20:25 定时序列领取与不对称互斥规则见
`references/reward.md`。

**定时任务**：任务表与 prompt 模板见 `references/cron.md`。

**到点提醒与私聊监视**：货轮/商船 schtasks 提醒与 chat_watch 常驻监视见
`references/chat.md`。

**暂停与恢复**：一键暂停/恢复全部自动化的协议（暂停即删除定时任务并记录
状态文件、恢复按暂停前清单重建、闯关不自动恢复）见 `references/pause.md`。

## 运行约定

- **串行执行，严禁并行**：所有脚本共享同一台设备，并行 = 点击互相干扰。
  后台长跑 PID 文件（`$TEMP/fkssj_battle.pid` / `$TEMP/fkssj_claim_seq.pid`）
  存在即视为对应长跑在跑，不得重复启动同一长跑。
- **闯关让位规则**：`battle_run.py` 与其他任务冲突时**其他任务优先**（先 `--stop`
  停止闯关、取日志尾部战果汇报，再执行该任务），完整流程见 `references/battle.md`。
- **claim_seq 互斥**：`claim_seq.py` 与其余脚本互斥（检查类定时任务遇其在跑跳过
  本轮；用户当面任务询问用户），完整规则见 `references/reward.md`。
- **长跑结果自推与标记兜底**：battle_run / claim_seq 启动即创建
  `$TEMP/fkssj_battle_done.pending` / `fkssj_claim_seq_done.pending`；脚本退出路径
  自动推送结果（日间直推微信 / 夜间写夜间日志 `$TEMP/fkssj_night_events.log`），
  成功后删标记；日间直推失败保留标记，由检查类任务与夜间总结推送顺路兜底补推后
  删除；让位/停止场景由 agent 推送后删标记。机制见 `references/battle.md`、
  `references/reward.md`、`references/cron.md`。
- **定时任务遇游戏未运行**：先询问是否启动游戏（3 分钟无回复视为不同意、跳过本轮），
  夜间 01:00:00-07:59:59 不询问直接跳过；见 `references/cron.md`。
- **同刻多任务优先级**：占设备越久优先级越靠后（提醒 → 夜间总结/每日服务总结 → 贸易 → 资源 → 领取；私聊监视遇长跑让位），默认触发时刻已错峰，自定义周期须错开分钟位（表见 `references/cron.md`）。
- **微信推送节流**：iLink 通道每 30 秒冷却一条，同 30 秒窗口内第二条起会被静默丢弃；脚本直推统一走 `game_lib.push_weixin()`，内置 `$TEMP/fkssj_push_guard` 30 秒推送锁（不足 30 秒自动补满再发），同刻互挤自动错开（货轮/商船 schtasks 整点、chat_watch :30 相位）；agent 会话推送（夜间总结与每日服务总结均 4 分、不同小时）靠分钟位错开；新建/改周期须保持即时任务分钟位错开（详见 `references/cron.md` 微信推送节流）。
- **一次只信 RESULT 行**：`[HH:MM:SS]` 前缀行是人类可读过程，`RESULT:` 行才是
  机器可解析结果；`ERROR` / `NOT_MAIN` / `STOPPED` / `STARTED` 开头的行是状态标记。
- **日志不出现按钮坐标**是本项目硬约定，改代码时不得在 print/log 中加坐标。
- **告警不弹窗**是本项目硬约定：所有脚本告警仅终端打印（[ALERT] 行），由 agent
  把结果转告用户，任何脚本不得弹阻塞式窗口。
- 每个单次脚本前置校验主界面（on_main），结束尽量还原回主界面。
- RapidOCR 首次加载需几秒属正常；`battle_run.py` 启动会打印模板加载行。
