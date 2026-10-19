# -*- coding: utf-8 -*-
"""货轮/商船到点提醒: 由 schtasks 每小时整点唤醒, 按内置时刻表直接推送提醒
取代原 agent cron 盲推会话(货轮/商船提醒), 实现 0 token 消耗的固定提醒:
  - 货轮: CARGO_HOURS 时刻表提醒"搁浅的货轮已在世界刷新!"
  - 商船: SHIP_HOURS 时刻表提醒"联盟商船刷新!"
  - 提醒停用清单: $TEMP/fkssj_reminder_off 一行列出停用的提醒名(cargo/ship, 空格
    或逗号分隔; 缺省或读取失败 = 全部照推), 切换只改该文件, 不必动代码, 也不必重注册计划任务
  - 同刻合并一条; 其余小时(含夜间)不在时刻表, 静默退出, 不推送不报错
纯提醒不占设备(无截屏无点击无游戏交互), 推送经 game_lib.push_weixin
(内置 30 秒推送锁, 与其余直推通道互斥); 直推失败多为撞上 iLink 微信通道
30 秒全局冷却(与对话回复/cron 投递共享), 失败后约 40 秒重试 1 次, 仍失败
则打印结果退出。
schtasks 注册/删除命令见 references/chat.md。
用法: python push_reminder.py   (由计划任务整点唤醒, 也可手动执行立即推一次)
      整点守卫: 非整点(分钟 > 10)手动执行默认跳过, 不推送假提醒; 确需立即验证加 --force
"""
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from game_lib import push_weixin, log_stat

CARGO_HOURS = set(range(8, 23))       # 货轮提醒小时(8-22)
SHIP_HOURS = {8, 11, 14, 17, 20, 23}  # 商船提醒小时
# 提醒停用清单: $TEMP/fkssj_reminder_off 单行列出停用的提醒名(cargo/ship; 缺省或读取失败 = 全部照推)。
# 切换只改这个文件: 不用动代码, 也不用重注册计划任务; 计划任务命令行不含取舍参数。


def reminder_off_names():
    """读停用清单: $TEMP/fkssj_reminder_off 一行列出停用的提醒名(空格/逗号分隔)。
    缺省/读取失败 = 空集(全部照推); 清单外的未知词忽略不计。"""
    import os, tempfile
    path = os.path.join(tempfile.gettempdir(), 'fkssj_reminder_off')
    try:
        with open(path) as f:
            return set(f.read().lower().replace(',', ' ').split())
    except OSError:
        return set()


def say(msg):
    """schtasks 用 pythonw 调用时 stdout 可能为 None, 安全打印"""
    try:
        print(msg)
    except Exception:
        pass


def main():
    off = reminder_off_names()
    now = datetime.now()
    h, mi = now.hour, now.minute
    cargo = h in CARGO_HOURS and 'cargo' not in off
    ship = h in SHIP_HOURS and 'ship' not in off
    if not (cargo or ship):
        return 0    # 全部停用或该小时无提醒, 静默退出
    # 整点守卫: 计划任务整点唤醒(允许整点后 10 分钟内的触发延迟);
    # 手动在非整点执行会推出"假刷新"提醒, 默认跳过, 确需验证加 --force。
    if mi > 10 and '--force' not in sys.argv[1:]:
        say('SKIP: 非整点(%02d:%02d), 不推送; 计划任务整点唤醒不受影响, 立即验证请加 --force' % (h, mi))
        return 0
    if cargo and ship:
        msg = '搁浅的货轮已在世界刷新, 联盟商船也刷新了!'
    elif cargo:
        msg = '搁浅的货轮已在世界刷新!'
    else:
        msg = '联盟商船刷新!'
    # 失败(多为撞上 iLink 30 秒全局冷却)后约 40 秒重试 1 次, 避开冷却窗;
    # 仍失败不补推, 下一整点照常提醒。
    ok = push_weixin(msg, max_tries=1)
    if not ok:
        say('RESULT: 首次推送失败, 40 秒后重试: %s' % msg)
        time.sleep(40)
        ok = push_weixin(msg, max_tries=1)
    if ok:
        log_stat('提醒', msg)
        say('RESULT: 已推送提醒 %s' % msg)
    else:
        say('RESULT: 推送失败(已重试1次): %s' % msg)
    return 0    # 提醒类失败也返回 0, 避免计划任务面板反复报错


if __name__ == '__main__':
    sys.exit(main())
