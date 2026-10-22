# 维护与校准 + 验收清单 + 部署

> **职责**：坐标/颜色常量维护、判定校准流程、验收清单与新机器部署。
> **何时读取**：需要修改坐标/颜色常量、校准判定、更新匹配模板，或部署到新机器时。

## 维护与校准（坐标/颜色全部集中在常量区）

- **坐标与颜色常量**：`scripts/game_lib.py` 顶部（贸易船三色、主界面特征色、资源裁剪框、
  各按钮坐标、游戏包名 PKG、设备占用互斥：占设备脚本名单 DEVICE_SCRIPTS / 进程枚举
  find_device_holder / 启动自检 ensure_device_free——枚举失败放行+WARN）、
  `scripts/check_ships.py` 顶部（交货被拒弹窗检测：检测点、
  "所需产品不足"弹窗紫色标题栏参考色、弹窗退出键；博物馆检测：入口/人气币气泡/寻宝
  入口/小队完成三点、返回键、展厅视角拖动与帧差判停参数；寻宝派遣：区域点击表、
  地图上下视角拖动、可寻宝判定点与参考色、选人/确认/槽位/派出判定色、区域退回键）、
  `scripts/gather_res.py`
  顶部（"自动"按钮旋转检测区、开启按钮坐标、帧差阈值与采样参数）、
  `scripts/battle_run.py` 顶部（胜负判定色、跳过/再战/
  下一关按钮）、`scripts/claim_online_reward.py` 顶部（城战/世界入口、在线奖励入口、
  各次领取按钮）、`scripts/claim_exp.py` 顶部（装备锻造入口、弹窗检测/关闭、返回键、
  经验气泡两点与橙色参考）、`scripts/claim_intel.py` 顶部（联盟情报入口、一键领取
  判定点与橙色参考、等级提升判定点与参考色、结算/返回按钮、"下次刷新时间"
  检测框/关键字/最少命中字数）、`scripts/claim_battle_reward.py` 顶部（闯关入口、
  闯关奖励入口、升级点判定点与无升级点参考色、挂机小时/上限 OCR 框、领取与
  结算/返回按钮、保底小时）、`scripts/chat_watch.py` 顶部（聊天入口/私聊页签/返回键坐标、主界面聊天入口
  红点粗筛点与私聊页签红点采样点、BGR 参考色及容差、检测相位秒）、
  `claim_seq.py` 的 INTERVALS（序列
  间隔秒数）和 `push_reminder.py` 顶部（货轮/商船提醒小时表；两者的启停是
  `$TEMP/fkssj_reminder_off` 停用清单文件而非代码常量，见 `chat.md`，勿改常量实现取舍）。
  改一处即全脚本生效，
  勿把数值散落进逻辑；`battle_run.py`/`claim_seq.py` 的 PID 与待推送标记文件名
  （$TEMP 下，所有 prompt 均按名引用，勿轻易改名）；`$TEMP/fkssj_push_guard`（推送锁）
  与 `$TEMP/fkssj_push.log`（推送尝试日志，每次直推追加一行 ok/fail(n/N)+原因）同属
  跨任务协议文件，勿改名；`$TEMP/fkssj_pause_state`（一键暂停的状态文件，
  "恢复自动化"的唯一恢复依据，协议见 `references/pause.md`）同属协议文件，
  暂停期间勿删。
- **主界面四重判定**（`game_lib.on_main`，勿随意删条件）：nav_stage 模板匹配 ≥ 0.80；
  (300,255) 不是资源界面特征色；左上区域 OCR 无"城战"二字；(65,1860) 为主界面特征色。
  历史教训：资源界面和城战界面 nav_stage 同样匹配 1.00，单模板不可靠；昼夜变化曾让
  容差 40 的像素判定失效，容差必须保持 10。
- **模板更新**：游戏改版后截图裁剪替换 `assets/nav_stage.png`、`assets/btn_fight.png`
  （保持原尺寸比例）。
- **校准流程**：改常量后必须实测——主界面（正例）、资源界面（反例）、贸易船三状态、
  交货被拒弹窗检测色（缺货交货时检测点应命中弹窗紫色）各跑一遍对应脚本/场景，
  确认判定与 RESULT 行正确后再交付。
- 修改脚本后同步维护 `references/scripts.md` 的脚本清单表。

## Verification Checklist

- [ ] 雷电模拟器在运行（adb server 5037 端口在监听）；游戏未跑先执行 `scripts/start_game.py`
- [ ] 雷电模拟器为平板版（配置分辨率 1920×1080、DPI 280）；不符先跑 `scripts/setup_emulator.py`
- [ ] 所有命令均为 Python 全路径 + skill scripts 全路径形式
- [ ] 任务脚本（如 `scripts/check_res.py`）启动时已有其他占设备脚本进程在跑则输出 `RESULT: XX未执行 已有YY进程占用设备` 且 exit 2，不执行任何设备操作；设备空闲时正常执行
- [ ] `scripts/check_main.py` 在主界面时输出 `MAIN nav_score=...`，exit 0
- [ ] `scripts/check_main.py` 启动时闯关（battle_run）在跑（PID 文件+进程枚举双确认）则先输出"检测到闯关进程在运行, 先终止..."并杀其进程树、清 PID 文件、善后战斗画面（战斗中点跳过，出结算/回主界面即止）；闯关正常结束调它恢复时（PID 文件已删）不触发终止
- [ ] `scripts/start_game.py` 游戏在跑时输出 `RESULT: 游戏运行中 主界面=是`，exit 0
- [ ] `scripts/stop_game.py` 输出 `RESULT: 游戏已停止`，exit 0
- [ ] `scripts/check_ships.py` 输出含三船状态的 `RESULT:` 行；缺货交货被拒时输出含"交货被拒(所需产品不足), 退回贸易页面"且 exit 2
- [ ] `scripts/check_res.py` 输出 `RESULT: 上限=... ... 不足=...`
- [ ] `scripts/gather_res.py` 无参数时报用法错误 exit 1
- [ ] `scripts/gather_res.py` 按剩余百分比自动定采集时长：>70% 1 分钟 / 40%-70% 3 分钟 / <40% 5 分钟，RESULT 含"(N分钟)"
- [ ] `scripts/gather_res.py` 带 `--no-recheck` 时 RESULT 仅"采集完成(N分钟) 回主界面=是"
- [ ] `scripts/gather_res.py` 进采集界面后自动检测"自动"按钮：已在旋转直接等待，未旋转先开启再等待
- [ ] `scripts/check_ships.py` 博物馆部分：进博物馆先移展厅视角到最左再检测人气币；随后必进寻宝界面数完成小队数（无论有无完成，0 支也进）并逐队收奖；有可派小队则上下视角逐区扫描，从队首可寻宝区域起逐区派遣小队直至派完（RESULT 含 寻宝奖励=N支 派出=N支），完成后回主界面
- [ ] `scripts/claim_exp.py` 有经验时输出"经验领取成功" exit 0；无经验输出"无经验可领" exit 0；不在主界面时自动恢复后继续
- [ ] `scripts/claim_intel.py` 领取后 RESULT 为"联盟情报领取完成"（有等级提升时附加" 等级提升N次"）exit 0；无可领输出"无联盟情报可领" exit 0（无可领时界面显示"下次刷新时间"倒计时，OCR 部分字样命中即直接退出循环）；不在主界面时自动恢复后继续
- [ ] `scripts/claim_battle_reward.py` 进奖励界面先清升级点（0.5s 节奏、上限 30 轮）；挂机小时 ≥ 上限-1 或 ≥ 23（保底）时输出"闯关奖励领取成功" exit 0；未达条件输出"闯关奖励未领取 挂机时长不足" exit 0；挂机时间 OCR 失败输出"闯关奖励领取不成功 挂机时间OCR失败" exit 1；不在主界面时自动恢复后继续
- [ ] `scripts/battle_run.py` 任何退出路径结束后自动恢复主界面并经 push_result 自推战果，末尾输出 RESULT 行
- [ ] `scripts/battle_run.py` 告警仅打印 [ALERT] 行，不弹窗
- [ ] `scripts/battle_run.py --stop` 未在运行时输出"闯关未在运行"，exit 0
- [ ] 后台长跑/常驻（battle_run / claim_seq / chat_watch）启动命令立即返回，agent 不前台等待（防会话超时）
- [ ] `scripts/game_status.py` 游戏在跑输出"RESULT: 游戏运行中" exit 0；模拟器/游戏未开输出对应状态 exit 2
- [ ] battle_run / claim_seq 启动后 `$TEMP` 下对应 `*_done.pending` 已创建
- [ ] 长跑退出自推后 pending 已删除（日间直推成功、夜间写夜间日志两条路径均验证）；日间直推失败时 pending 保留，由检查类任务/夜间总结推送兜底补推后删除
- [ ] `game_lib.push_weixin()` 失败自动重试：默认共 3 次、间隔由推送锁拉开约 30 秒；每次尝试在 `$TEMP/fkssj_push.log` 追加一行 `[MM-DD HH:MM:SS] ok/fail(n/N): 消息前缀 | 原因 | 输出尾`（成功行只有消息前缀）；提醒类 push_reminder 传 max_tries=1、失败后约 40 秒外层重试 1 次（避开 iLink 冷却），仍失败不补推、返回 0，下次整点照常
- [ ] `scripts/claim_online_reward.py` 传 1-7 序号领取对应次在线奖励后回主界面，exit 0；参数非 1-7 时 exit 1
- [ ] `scripts/claim_seq.py --stop` 未在运行时输出"未在运行"，exit 0
- [ ] `scripts/chat_watch.py` 常驻启动后每 2 分钟按相位检测一轮：主界面无聊天入口红点时零点击跳过，有红点才进聊天页确认后软回主界面；占设备脚本进程在跑时让位跳过（可临时起一个文件名含名单子串的 python 探测脚本验证让位行）、枚举失败保守跳过、非主界面零点击跳过（绝不主动退回）；`--stop` 输出停止 RESULT 行，未在运行时输出"私聊监视未在运行" exit 0
- [ ] `scripts/push_reminder.py` 手动验证（先把 `$TEMP/fkssj_reminder_off` 删除或清空，避免被停用清单滤掉；再写 `cargo ship` 验证全部停用静默生效）：货轮小时推货轮提醒、商船小时推商船提醒、同刻（8/11/14/17/20 点）推合并文案、其余小时静默退出
- [ ] `schtasks /Query /TN "fkssj_push_reminder"` 显示任务已注册（每小时整点触发；注册/删除命令见 `references/chat.md`）
- [ ] 夜间日志 `$TEMP/fkssj_night_events.log` 行格式 "[MM-DD HH:MM] 任务名: 摘要"（任务名固定：闯关/城战奖励/贸易/资源/经验/情报/私聊），夜间总结推送后文件已清空
- [ ] 每日统计 `$TEMP/fkssj_stats.log` 行格式 "[MM-DD HH:MM] 服务名: 摘要"（服务名固定：贸易/资源/城战奖励/经验/情报/闯关/提醒/私聊/夜间总结）；每天 01:04 每日服务总结推送"当前开启服务 + 各服务今日完成次数"（夜间窗口内唯一允许直推的消息）后文件已清空
- [ ] "暂停自动化"后：/cron 无【fkssj …】任务、chat_watch 与长跑 PID 文件消失、`$TEMP/fkssj_reminder_off` 为 cargo ship、`$TEMP/fkssj_pause_state` 已生成；暂停前确有自动化在开时【fkssj 暂停询问】任务已建（全关状态不建）
- [ ] "恢复自动化"后：任务按暂停前清单与记录的表达式重建（prompt 优先 `local/commands.md` 完整路径版）、chat_watch 按暂停前状态重启、停用清单还原为暂停前内容、状态文件与询问任务已删除；闯关不自动恢复
- [ ] `scripts/check_main.py` 第 2 次尝试非城战点兜底按钮、城战点"基地"按钮，之后剩余次数按界面类型层层退回，全部尝试后等 3 秒终检（最后一次点击生效不算失败）
- [ ] "fkssj帮助"按 `templates/help.txt` 模板逐行输出树结构功能清单（保持换行与缩进）
- [ ] 本机部署：`local/commands.md` 存在时优先逐字使用其中的完整路径命令
- [ ] 定时任务开启前 `/cron list` 查重；关闭时按【fkssj …】标识找到任务再删除
- [ ] 每次汇报均符合输出规范三字段逐行格式（check_main/force_main 成功时仅"已回到主界面"）
- [ ] 所有脚本日志与汇报中无按钮坐标

## 部署与开源说明

- 依赖见 `requirements.txt`（Python 3.12+），许可证见 `LICENSE`（AGPL-3.0）。
- `local/` 目录是本机部署时生成的完整路径命令清单，属机器私有配置，已被
  `.gitignore` 排除，不随仓库分发；母 SKILL.md"运行位置"节规定该文件存在时
  必须优先逐字使用其中的命令。
- 部署到新机器：安装 `requirements.txt` 依赖 → 确认雷电模拟器为平板版预设
  （跑 `scripts/setup_emulator.py`）→ 按本文件上方"维护与校准"的校准流程实测
  判定 → 需要提醒/监视时按 `references/chat.md` 注册 Windows 计划任务
  `fkssj_push_reminder`（重启后仍有效）并后台启动私聊监视（电脑重启后不自启，
  需重新开启）。
- 版本升级（skill 分发文件更新）后：`local/commands.md` 内已固化旧版任务 prompt
  不会自动跟随，重建活 cron 任务前必须先按新 `references/cron.md` 模板同步重写
  该文件，防止按旧表达式/旧语义重建已废弃任务；"恢复自动化"按该文件重建任务，
  同样依赖其与最新模板一致（暂停/恢复协议见 `references/pause.md`）。
