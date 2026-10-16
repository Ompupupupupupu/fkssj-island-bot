---
name: fkssj-island-bot
description: "Use when 用户提到 fkssj、海岛经营游戏、fkssj帮助/ssj帮助、游戏启动或停止、贸易船检查或交货、资源检查或采集、自动闯关、主界面检查或强制恢复、开启或关闭定时任务（自动检查贸易/自动检查资源/搁浅的货轮提醒/联盟商船提醒）。本 skill 通过雷电模拟器的 adb server (127.0.0.1:5037) 驱动游戏 com.gx.sw.qa.fkssj003.esj，提供单次执行的自动化脚本：模拟器平板版配置检查修正、启动/停止游戏、检查并恢复主界面、三船贸易检查+自动交货、7 种资源 OCR 检查、单资源采集（时长按剩余百分比自动定 1/3/5 分钟，采后自动复查全部资源，多资源用 --no-recheck 分组编排）、强制重启回主界面、自动闯关长跑；并支持用 /cron 编排定时任务：自动检查贸易/资源（默认每 30 分钟可指定周期，夜间 01:00-08:00 只执行不推送，资源不足自动采集）、搁浅货轮整点提醒（每天 8-22 点）、联盟商船定点提醒（每天 8/11/14/17/20/23 点）。脚本检查与操作分离，输出 RESULT 汇总行与语义化 exit code。"
version: 1.4.0
author: "Ompupupupupupu"
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [fkssj, game-automation, adb, ldplayer, ocr, trade-ships, resource-gathering, battle-loop]
    category: automation
    related_skills: [android-device-automation]
---

# fkssj 海岛经营游戏自动化（单次脚本工具包）

## Overview

雷电模拟器 9（`emulator-5554`）中海岛经营游戏 `com.gx.sw.qa.fkssj003.esj`
的自动化脚本集。**环境要求：雷电平板版预设**（配置分辨率 1920×1080、DPI 280；
竖屏显示下 adb 截图为 1080×1920，全部坐标基于此；不符时用 `scripts/setup_emulator.py`
检查修正）。设计原则：**单次执行、检查与操作分离、结果可解析**——每个脚本跑一轮
就退出，stdout 末行输出机器可解析的 `RESULT:` 汇总，exit code 表达语义（0 正常 /
1 失败 / 2 需要用户行动）。

脚本通过本机 adb server（127.0.0.1:5037，雷电模拟器启动后自动在跑）直连设备，
无需 adb.exe 在 PATH。屏幕感知 = 截图 + 模板匹配 + 固定像素颜色判定 + RapidOCR。

## When to Use

- 用户说"检查模拟器配置 / 分辨率不对 / 平板版设置" → `scripts/setup_emulator.py`（检查+自动修正）
- 用户说"启动游戏 / 打开游戏" → `scripts/start_game.py`（已运行则报告状态不重启）
- 用户说"停止游戏 / 关掉游戏" → `scripts/stop_game.py`
- 用户说"检查贸易 / 船回来了吗 / 交货" → `scripts/check_ships.py`（检查+自动交货一体）
- 用户说"看看资源 / 鱼够不够 / 木材还剩多少" → `scripts/check_res.py`（只读 OCR）
- 用户说"采集鱼 / 去钓鱼 / 收集海藻" → `scripts/gather_res.py`（时长按剩余百分比自动定 1/3/5 分钟，完成后自动复查全部资源）
- 需要采集多种资源 → 按"典型编排 - 多资源采集"的分组规则决定采哪些：每组只采组内剩余最少一种
- 用户说"闯关 / 打关卡 / 继续打" → `scripts/battle_run.py`（长跑循环，Ctrl+C 中断）
- 用户说"回主界面 / 游戏卡在某个界面" → `scripts/check_main.py`，失败再 `scripts/force_main.py`
- 周期性维护 → 编排流程见下文"典型编排"
- 用户说"fkssj帮助 / ssj帮助" → 按 `templates/help.txt` 模板逐行输出功能清单（保持模板换行）
- 用户说"开启/关闭 + 自动检查贸易 / 自动检查资源 / 搁浅的货轮提醒 / 联盟商船提醒"
  → 按下文"定时任务与提醒"节用 /cron 创建或删除定时任务

不适用于：其他游戏、其他分辨率、其他模拟器。

## 运行位置（强指令）

- **必须从本 skill 的 scripts/ 目录运行脚本**，不得使用其他来源的副本。
- **本机部署优先规则**：若本 skill 根目录存在 `local/commands.md`（部署时生成的
  完整路径命令清单），**必须先读取它并逐字使用其中的命令，不得自行改写路径**；
  不存在时按通用模板以实际安装位置展开。
- 通用命令模板（`<PYTHON>` = 已装依赖的 Python 解释器，`<SKILL_DIR>` = 本 skill
  安装根目录）：

```text
<PYTHON> <SKILL_DIR>/scripts/<脚本名>.py
```

- 路径一律用正斜杠原生形式（见 Common Pitfalls 第 7 条）。

## 前提条件（缺一不可，先检查再跑）

1. **雷电模拟器 9 已启动**（adb server 随模拟器自动运行）。连接失败报
   `ConnectionRefusedError` / `no devices` = 模拟器没开。游戏未运行时可先跑
   `scripts/start_game.py`，它会冷启动游戏并等待停到主界面。
2. **雷电模拟器为平板版预设**：配置分辨率 1920×1080、DPI 280（竖屏显示下 adb 截图
   1080×1920，本 skill 全部坐标基于此）。首次使用或怀疑环境不符时先跑
   `scripts/setup_emulator.py`（非默认安装位置加 `--ld-dir`，多实例加 `--instance`）：
   符合 exit 0；不符自动修正，模拟器运行中修正后
   exit 2 需重启模拟器生效（重启后重跑验证；仍不符则关闭模拟器再跑本脚本）。
3. **Python 3.12+**（已装 `requirements.txt` 中的依赖：opencv-python、
   rapidocr_onnxruntime；实测 3.11 与 rapidocr-onnxruntime 不兼容）。
4. 脚本位于本 skill 的 `scripts/` 目录，匹配模板位于 `assets/`（`assets/nav_stage.png`、
   `assets/btn_fight.png`，脚本按相对路径自动定位，skill 目录整体搬移不影响运行）。
   运行时截图写入 `%TEMP%/fkssj_skill_shots/`。
5. **仅支持单模拟器实例**（emulator-5554 / 实例 leidian0）；多实例环境请先关闭其他
   实例再运行脚本。

## 脚本清单

| 文件 | 角色 | 参数 | exit code |
|---|---|---|---|
| `scripts/game_lib.py` | 共享库（常量+判定函数），被各脚本导入，不直接运行 | - | - |
| `scripts/pyadb.py` | adb 直连库，被 game_lib 导入，不直接运行 | - | - |
| `scripts/setup_emulator.py` | 检查并修正雷电模拟器基础配置：要求平板版配置分辨率 1920×1080、DPI 280；不符时自动改写实例配置；模拟器运行中修正后需重启生效（重启后重跑验证，仍不符则关模拟器再跑本脚本修正后启动）；安装目录自动探测，未命中需显式指定 | 可选 `--ld-dir <雷电安装目录>`、`--instance <实例名，默认 leidian0>` | 0=符合或已修正(模拟器未运行)；1=读写失败或安装目录未找到；2=已修正需重启模拟器 |
| `scripts/start_game.py` | 启动游戏：已运行则报告状态不重启；未运行则冷启动+轮询等主界面（上限 60 秒），超时走 check_main 兜底 | 无 | 0=游戏运行中；1=启动失败 |
| `scripts/stop_game.py` | 停止游戏：force-stop 后 2 秒复检，仍在则重试一次 | 无 | 0=已停止（含本来就未运行）；1=停止失败 |
| `scripts/check_main.py` | 检查是否在主界面；不在则自动恢复：第 1 次按界面类型点按钮（城战→"基地"，其他→返回），第 2 次尝试点兜底按钮，之后 2 次复检（每次等 3 秒）未回主界面再点返回按钮层层退回 | 无 | 0=已在/已回主界面；1=恢复失败 |
| `scripts/check_ships.py` | 三艘贸易船状态检查 + 自动收货交货：未回来→跳过；已回来→收货→结算→交货；货物不全→直接交货，1 秒后复检确认 | 无 | 0=处理完；1=不在主界面或未知状态；2=有船货物不足（需用户补货） |
| `scripts/check_res.py` | 7 种资源剩余数量 + 上限 OCR（只读，不采集），低于上限 70% 标记不足 | 无 | 0=完成；1=不在主界面；2=上限 OCR 失败 |
| `scripts/gather_res.py` | 采集一种资源，时长按剩余百分比自动判定：>70% 采 1 分钟、40%-70% 采 3 分钟、<40% 采 5 分钟（OCR 失败默认 3 分钟）；完成后自动回主界面并复检（3 次重试），随后自动复查全部资源剩余（同 check_res，附在 RESULT 行）；`--no-recheck` 跳过复查（多资源连续采集时用） | 资源名或序号 1-7：鱼/塑料/木材/碎布/废金属/玻璃/海藻；可选 `--no-recheck` | 0=采集完成（RESULT 含时长与全资源剩余）；1=参数错误/不在主界面/退出失败 |
| `scripts/force_main.py` | 强制回主界面（check_main 失败时用）：重启游戏→轮询等加载（上限 60 秒）→超时再跑一次 check_main 兜底 | 无 | 0=已在/已回主界面；1=强制恢复失败 |
| `scripts/battle_run.py` | 自动闯关长跑：开战 12 秒后跳过看结果，胜→直接下一关，败→再战；连续 5 败或单场超 15 分钟告警退出（告警只打印 [ALERT] 行，不弹窗，由 agent 转告用户）；**任何退出路径（告警/中断/异常）结束后自动调 check_main.py 恢复主界面**，末尾输出 RESULT 行 | 无（需人在场，Ctrl+C 中断） | 0=结束且回主界面成功；1=异常退出或回主界面失败（再走 force_main.py 恢复链） |

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
- 连续运行多个脚本时，每个脚本单独一块上述格式，块之间空一行，按执行顺序排列，不要合并。
- 汇报只保留状态与结果，不要复述 `[HH:MM:SS]` 前缀的过程日志。
- **任何输出不得出现按钮坐标**（本项目硬约定）。
- exit 2 = 需要用户行动（如贸易船缺货、OCR 失败），在"下一步"中写明给用户的建议。
- `battle_run.py` 被中断或告警退出后，按同样格式汇报末尾统计行（胜/负/用时），
  "结果"字段另含结束后的 RESULT 行（已回主界面/回主界面失败）。
- `gather_res.py` 默认在 RESULT 行附带采集后复查的全资源剩余（与 check_res 同构），
  按 check_res 示例同样方式逐行展开；带 `--no-recheck` 时 RESULT 仅"采集完成(N分钟) 回主界面=是"。

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

**收工/开工**：

```text
<PYTHON> <SKILL_DIR>/scripts/stop_game.py
```

```text
<PYTHON> <SKILL_DIR>/scripts/start_game.py
```

**周期维护**（如"帮我做一轮日常"，串行执行）：

```text
<PYTHON> <SKILL_DIR>/scripts/check_main.py
```

```text
<PYTHON> <SKILL_DIR>/scripts/check_ships.py
```

```text
<PYTHON> <SKILL_DIR>/scripts/check_res.py
```

**多资源采集（分组规则，必须遵守）**：check_res 的 RESULT 行"不足"列表含多种资源时，
按采集界面分组：`[鱼]`、`[塑料, 木材, 碎布]`、`[废金属, 玻璃, 海藻]`。

- 同组的多种资源不足 → 只采集**组内剩余数量最少**的那一种，运行一次。
- 不足资源分布在不同组 → 每组各运行一次（各自取组内最少的）。
- 连续采集时每个 `gather_res.py` 都带 `--no-recheck` 跳过逐次复查，串行执行；
  **全部采集完成后统一跑一次 `check_res.py` 复查**，按输出规范汇报。
- 只采一种资源时不加 `--no-recheck`（脚本采后自动复查，无需再跑 check_res）。

```text
<PYTHON> <SKILL_DIR>/scripts/gather_res.py "鱼" --no-recheck
```

（海藻则把 `"鱼"` 换成 `"海藻"`，或用序号 1-7；单资源场景去掉 `--no-recheck`。）

**恢复链**：`check_main.py` exit 1 → `force_main.py` → 仍 exit 1 才报告用户人工处理
（可能被模态弹窗卡住，不要乱点，如实上报）。

**闯关**：确认无其他脚本在跑 → `battle_run.py` 前台运行 → 用户中断或告警退出后
自动恢复主界面，按输出规范汇报统计与末尾 RESULT 行。

## 定时任务与提醒（/cron 编排）

用户说"开启/关闭 + 任务名"时，用 Hermes 的 `/cron` 管理定时任务：

- 开启：先 `/cron list` 查重，同类任务已存在则告知用户、不重复创建；
  不存在则用 `/cron add "<cron 表达式>" "<任务 prompt>"` 创建。
- 关闭：`/cron list` 找到对应任务（prompt 首行含【fkssj …】标识）后删除该任务。
- 用户指定检查周期（如"每 1 小时"）→ 换算成对应 cron 表达式；
  提醒类任务是游戏刷新时间，固定不可改。

| 任务 | 开启触发词 | 默认 cron 表达式 | 关闭触发词 |
|---|---|---|---|
| 自动检查贸易 | "开启自动检查贸易" | `*/30 * * * *` | "关闭自动检查贸易" |
| 自动检查资源 | "开启自动检查资源" | `*/30 * * * *` | "关闭自动检查资源" |
| 搁浅的货轮提醒 | "开启搁浅的货轮提醒"、"提醒货轮" | `0 8-22 * * *` | "关闭搁浅的货轮提醒" |
| 联盟商船提醒 | "开启联盟商船提醒" | `0 8,11,14,17,20,23 * * *` | "关闭联盟商船提醒" |

任务 prompt 模板（`/cron add` 第二参数照抄；命令必须写完整路径——
执行会话没有当前对话上下文，短名脚本无法定位。本机部署存在
`local/commands.md` 时直接用其中的完整路径版 prompt；其他部署把
`<PYTHON>`/`<SKILL_DIR>` 替换为实际安装路径）：

自动检查贸易：

```text
【fkssj 自动检查贸易】依次运行两条命令:
<PYTHON> <SKILL_DIR>/scripts/check_main.py
<PYTHON> <SKILL_DIR>/scripts/check_ships.py
把 check_ships.py 的 RESULT 行原样汇报给用户; 若当前时间在 01:00-08:00 之间, 只执行检查, 不要向用户推送任何结果。
```

自动检查资源：

```text
【fkssj 自动检查资源】先运行:
<PYTHON> <SKILL_DIR>/scripts/check_main.py
再运行同目录的 check_res.py。若其 RESULT 行的"不足"列表非空: 按 [鱼] [塑料,木材,碎布] [废金属,玻璃,海藻] 分组, 每组只采组内剩余最少的一种(运行同目录 gather_res.py 并传资源名参数, 连续采集加 --no-recheck), 全部采完统一再跑一次同目录 check_res.py 复查。把检查与采集结果汇报给用户; 若当前时间在 01:00-08:00 之间, 只执行, 不要向用户推送任何结果。
```

搁浅的货轮提醒：

```text
【fkssj 搁浅货轮提醒】直接向用户推送这条提醒: 搁浅的货轮已在世界刷新!
```

联盟商船提醒：

```text
【fkssj 联盟商船提醒】直接向用户推送这条提醒: 联盟商船刷新!
```

规则：
- 检查类任务（贸易/资源）夜间 01:00-08:00 只执行不推送，该规则已写进
  任务 prompt，无需另建夜间任务。
- 提醒类任务（货轮/商船）是固定时间盲推送，与游戏实际刷新状态无关。

## 运行约定

- **串行执行，严禁并行**：所有脚本共享同一台设备，并行 = 点击互相干扰。
  `battle_run.py` 是无限循环，与其余脚本互斥；运行期间禁止调用任何 check_*/gather_*/start_*/stop_*。
- **一次只信 RESULT 行**：`[HH:MM:SS]` 前缀行是人类可读过程，`RESULT:` 行才是
  机器可解析结果；`ERROR` / `NOT_MAIN` / `STOPPED` / `STARTED` 开头的行是状态标记。
- **日志不出现按钮坐标**是本项目硬约定，改代码时不得在 print/log 中加坐标。
- **告警不弹窗**是本项目硬约定：所有脚本告警仅终端打印（[ALERT] 行），由 agent
  把结果转告用户，任何脚本不得弹阻塞式窗口。
- 每个单次脚本前置校验主界面（on_main），结束尽量还原回主界面。
- RapidOCR 首次加载需几秒属正常；`battle_run.py` 启动会打印模板加载行。

## 互斥与故障排查

| 现象 | 原因 | 处理 |
|---|---|---|
| `ConnectionRefusedError` / `no devices` | 模拟器未启动 | 先启动雷电模拟器，再跑 `start_game.py` |
| setup_emulator exit 2 | 配置修正需重启模拟器才生效 | 重启后重跑 setup_emulator 验证；仍不符则关闭模拟器再跑本脚本修正后启动 |
| start_game 超时后自动恢复成功 | 游戏启动后有弹窗遮挡 | 属预期兜底路径，无需处理 |
| check_main 反复 NOT_MAIN（兜底按钮也无效） | 模态弹窗遮挡（如联盟成员列表） | `force_main.py` 重启游戏兜底 |
| check_ships exit 2 | 船货物不全，无法交货 | 告知用户手动补货，属预期行为 |
| check_res exit 2 | 上限 OCR 失败 | 重跑一次；仍失败检查 CAP_BOX 裁剪框 |
| 主界面误判 | 游戏昼夜光照导致像素色漂移 | 容差 COLOR_TOL 已设 10，勿调大 |

## 维护与校准（坐标/颜色全部集中在常量区）

- **坐标与颜色常量**：`scripts/game_lib.py` 顶部（贸易船三色、主界面特征色、资源裁剪框、
  各按钮坐标、游戏包名 PKG）和 `scripts/battle_run.py` 顶部（胜负判定色、跳过/再战/
  下一关按钮）。改一处即全脚本生效，勿把数值散落进逻辑。
- **主界面四重判定**（`game_lib.on_main`，勿随意删条件）：nav_stage 模板匹配 ≥ 0.80；
  (300,255) 不是资源界面特征色；左上区域 OCR 无"城战"二字；(65,1860) 为主界面特征色。
  历史教训：资源界面和城战界面 nav_stage 同样匹配 1.00，单模板不可靠；昼夜变化曾让
  容差 40 的像素判定失效，容差必须保持 10。
- **模板更新**：游戏改版后截图裁剪替换 `assets/nav_stage.png`、`assets/btn_fight.png`
  （保持原尺寸比例）。
- **校准流程**：改常量后必须实测——主界面（正例）、资源界面（反例）、贸易船三状态
  各跑一遍对应脚本，确认判定与 RESULT 行正确后再交付。
- 修改脚本后同步维护本 SKILL.md 的脚本清单表。

## Common Pitfalls

1. **并行跑脚本**。adb 点击是全局的，两个进程同时点 = 乱点。永远串行。
2. **不看 exit code 只看打印**。exit 2 是"需要用户行动"的信号（缺货/OCR 失败），
   必须向用户转述 RESULT 行。
3. **模拟器没开就跑**。game_lib 导入时即初始化 adb 连接与 OCR，会直接抛异常。
4. **在 battle_run 运行中调 gather_res**。会被 battle_run 的点击流打断采集计秒，
   造成退出失败误报。
5. **force_main 运行前不确认无其他脚本在跑**。它重启游戏，会掐断任何在途操作。
6. **以为 RESULT 在最后一行之外**。个别路径（如 check_ships 部分成功）RESULT 在
   返回主界面之后打印，exit code 才是权威。
7. **在 Git Bash 里用 `/c/...` 路径调 python**。原生 python.exe 不做 MSYS 路径转换，
   `python /c/Users/.../check_main.py` 会报 `can't open file 'C:\c\Users\...'`（no such
   file)。一律用正斜杠原生路径，例如：

```text
<PYTHON> <SKILL_DIR>/scripts/check_main.py
```

## Verification Checklist

- [ ] 雷电模拟器在运行（adb server 5037 端口在监听）；游戏未跑先执行 `scripts/start_game.py`
- [ ] 雷电模拟器为平板版（配置分辨率 1920×1080、DPI 280）；不符先跑 `scripts/setup_emulator.py`
- [ ] 所有命令均为"运行位置"节定义的 Python 全路径 + skill scripts 全路径形式
- [ ] `scripts/check_main.py` 在主界面时输出 `MAIN nav_score=...`，exit 0
- [ ] `scripts/start_game.py` 游戏在跑时输出 `RESULT: 游戏运行中 主界面=是`，exit 0
- [ ] `scripts/stop_game.py` 输出 `RESULT: 游戏已停止`，exit 0
- [ ] `scripts/check_ships.py` 输出含三船状态的 `RESULT:` 行
- [ ] `scripts/check_res.py` 输出 `RESULT: 上限=... ... 不足=...`
- [ ] `scripts/gather_res.py` 无参数时报用法错误 exit 1
- [ ] `scripts/gather_res.py` 按剩余百分比自动定采集时长：>70% 1 分钟 / 40%-70% 3 分钟 / <40% 5 分钟，RESULT 含"(N分钟)"
- [ ] `scripts/gather_res.py` 带 `--no-recheck` 时 RESULT 仅"采集完成(N分钟) 回主界面=是"
- [ ] `scripts/battle_run.py` 任何退出路径结束后自动调 check_main 恢复主界面，末尾输出 RESULT 行
- [ ] `scripts/battle_run.py` 告警仅打印 [ALERT] 行，不弹窗
- [ ] `scripts/check_main.py` 第 2 次尝试点兜底按钮，之后剩余次数点返回按钮层层退回
- [ ] "fkssj帮助"按 `templates/help.txt` 模板逐行输出（保持换行）
- [ ] 本机部署：`local/commands.md` 存在时优先逐字使用其中的完整路径命令
- [ ] 定时任务开启前 `/cron list` 查重；关闭时按【fkssj …】标识找到任务再删除
- [ ] 每次汇报均符合"输出规范"三字段逐行格式（check_main/force_main 成功时仅"已回到主界面"）
- [ ] 所有脚本日志与汇报中无按钮坐标

## 部署与开源说明

- 依赖见 `requirements.txt`（Python 3.12+），许可证见 `LICENSE`（MIT）。
- `local/` 目录是本机部署时生成的完整路径命令清单（见"运行位置"节），
  属机器私有配置，已被 `.gitignore` 排除，不随仓库分发。
- 部署到新机器：安装 `requirements.txt` 依赖 → 确认雷电模拟器为平板版预设
  （跑 `scripts/setup_emulator.py`）→ 按"维护与校准"节的校准流程实测判定。
