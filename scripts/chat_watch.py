# -*- coding: utf-8 -*-
"""私聊未读监视: 常驻循环检测游戏内私聊未读红点, 发现未读直接推送提醒
流程(每 2 分钟一轮, tick 相位对齐偶数分钟 :30 秒, 避开整点触发的贸易/资源任务):
  1. 互斥让位(私聊监视优先级最低, 其他任务优先运行): 闯关/城战奖励后台 PID
     文件存在, 或进程枚举发现其他占设备脚本 python 进程在跑(DEVICE_SCRIPTS
     名单, 排除自身) -> 本轮跳过(枚举失败也保守跳过本轮)
  2. 主界面四条件判定(game_lib.on_main), 非主界面 -> 零点击直接跳过本轮,
     绝不主动点击退回(防打断采集/检查等正在使用设备的任务; 卡子页面的恢复
     由每 30 分钟会话的 check_main 负责, 监视只在主界面做只读检测)
  3. 两层检测: 先粗筛主界面聊天入口红点((852,1669)), 无红点零点击结束本轮;
     有红点才进聊天页 -> 切私聊页签 -> 截屏采样私聊页签红点颜色确认
  4. 检测后立即返回主界面(逐次点返回键并复检, 最多3次; 恢复失败不强制, 下轮重试)
推送规则:
  - 检测到未读: 日间经 hermes 直推提醒; 夜间只写夜间日志由 08:04 夜间总结统一推送
  - 防重推: 红点持续存在只推一次, 红点消失后重置; 直推失败不置已推标志, 下轮重试
PID 文件 $TEMP/fkssj_chat_watch.pid 记录后台进程; --stop 按 PID 杀进程树停止
用法: python chat_watch.py          (常驻监视, 供后台启动, 见 references/chat.md)
      python chat_watch.py --stop   (停止监视)
"""
import os
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from game_lib import shot, on_main, tap, log, is_night, push_weixin, log_night_event, log_stat

TICK_PHASE = 30                    # tick 相位: 每个检测周期的第几秒(错开整点任务高峰)
TICK_PERIOD = 120                  # 检测周期(秒): 每 2 分钟一轮
PID_FILE = os.path.join(os.environ.get('TEMP', '.'), 'fkssj_chat_watch.pid')
MUTEX_PIDS = [                     # 长跑任务 PID 文件(存在即让位)
    os.path.join(os.environ.get('TEMP', '.'), 'fkssj_battle.pid'),
    os.path.join(os.environ.get('TEMP', '.'), 'fkssj_claim_seq.pid'),
]
DEVICE_SCRIPTS = [                 # 占设备脚本名单(进程命令行命中即让位, 排除自身)
    'check_main.py', 'check_ships.py', 'check_res.py', 'gather_res.py',
    'claim_online_reward.py', 'claim_seq.py', 'claim_exp.py', 'claim_intel.py',
    'claim_battle_reward.py',
    'battle_run.py',
    'start_game.py', 'stop_game.py', 'force_main.py', 'status_check.py',
]
# game_status.py(只读 adb 探测) / push_reminder.py(无截屏无点击) 不占设备, 不入名单
PS_QUERY = ('Get-CimInstance Win32_Process -Filter "Name LIKE \'python%\'" | '
            'ForEach-Object { "$($_.ProcessId)|$($_.CommandLine)" }')

BADGE_X, BADGE_Y = 852, 1669       # 主界面聊天入口未读红点采样点(第一层粗筛)
CHAT_X, CHAT_Y = 540, 1700         # 主界面聊天入口按钮
PM_X, PM_Y = 660, 180              # 聊天页私聊页签
DOT_X, DOT_Y = 1034, 280           # 私聊页签未读红点采样点
DOT_BGR = (87, 41, 255)            # 红点参考色(实测)
DOT_TOL = 25                       # 红点判定每通道容差
BACK_X, BACK_Y = 10, 1760          # 通用返回键
RECOVER_GAP = 0.8                  # 每次点击后等待界面切换的秒数


def write_pid():
    """写 PID 文件, 供 --stop 查找"""
    try:
        with open(PID_FILE, 'w') as f:
            f.write(str(os.getpid()))
    except Exception as e:
        print('WARN 写PID文件失败: %r' % e)


def remove_pid():
    try:
        os.remove(PID_FILE)
    except OSError:
        pass


def stop():
    """按 PID 文件停止后台监视进程(杀进程树)"""
    if not os.path.exists(PID_FILE):
        print('RESULT: 私聊监视未在运行')
        return 0
    try:
        with open(PID_FILE) as f:
            pid = f.read().strip()
        r = subprocess.run(['taskkill', '/PID', pid, '/F', '/T'],
                           capture_output=True)
    except Exception as e:
        print('RESULT: 私聊监视停止失败 %r' % e)
        return 1
    remove_pid()
    if r.returncode != 0:
        print('RESULT: 私聊监视未在运行(进程已不存在)')
        return 0
    print('RESULT: 私聊监视已停止')
    return 0


def busy():
    """闯关/城战奖励后台任务运行中(独占设备), 监视让位"""
    return any(os.path.exists(p) for p in MUTEX_PIDS)


def other_device_process():
    """枚举 python/pythonw 进程命令行(PowerShell CIM, 本机 wmic 已移除不可用),
    命中占设备脚本名单(排除自身进程)则让位。
    返回值: 命中的脚本名 / None=无占用 / ''=枚举失败(调用方保守跳过本轮)。
    命令行中非 ASCII 参数按 replace 解码, 名单全 ASCII 不受影响。"""
    try:
        r = subprocess.run(
            ['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass',
             '-Command', PS_QUERY],
            capture_output=True, text=True, encoding='utf-8',
            errors='replace', timeout=15)
        out = r.stdout or ''
        mypid = str(os.getpid())
        for line in out.splitlines():
            line = line.strip()
            if '|' not in line:
                continue
            pid, cmd = line.split('|', 1)
            if not pid.isdigit() or pid == mypid:
                continue
            for name in DEVICE_SCRIPTS:
                if name in cmd:
                    return name
    except Exception:
        return ''
    return None


def wait_tick():
    """等待到下一个检测相位(周期 TICK_PERIOD 秒, 相位对齐第 TICK_PHASE 秒)"""
    sec = time.time() % TICK_PERIOD
    time.sleep((TICK_PHASE - sec) % TICK_PERIOD or TICK_PERIOD)


def has_dot(img, x, y):
    """采样 (x,y) 像素颜色对比红点参考色: True=红点存在"""
    if img is None:
        return False
    b, g, r = img[y, x]
    return (abs(int(b) - DOT_BGR[0]) <= DOT_TOL and
            abs(int(g) - DOT_BGR[1]) <= DOT_TOL and
            abs(int(r) - DOT_BGR[2]) <= DOT_TOL)


def back_soft():
    """从私聊页返回主界面: 逐次点返回键并复检(每次间隔 RECOVER_GAP), 最多3次;
    不强制恢复(失败由下轮重试)"""
    for _ in range(3):
        tap(BACK_X, BACK_Y)
        time.sleep(RECOVER_GAP)
        if on_main(shot()):
            return True
    return False


def check_round(notified):
    """单轮检测: 返回更新后的已提醒标志(红点持续存在期间保持已提醒不重复推)"""
    if busy():
        log('闯关/城战进行中, 本轮跳过')
        return notified
    who = other_device_process()
    if who:
        log('%s 运行中, 私聊监视让位, 本轮跳过' % who)
        return notified
    if who == '':
        log('WARN 进程枚举失败, 保守让位本轮')
        return notified
    img = shot()
    if not on_main(img):
        log('非主界面(设备可能正被使用), 零点击跳过本轮')
        return notified
    # 第一层: 主界面聊天入口红点粗筛, 无红点零点击结束本轮(减少点击)
    if not has_dot(img, BADGE_X, BADGE_Y):
        log('主界面无聊天未读红点, 本轮跳过')
        return notified
    tap(CHAT_X, CHAT_Y)
    tap(PM_X, PM_Y)
    unread = has_dot(shot(), DOT_X, DOT_Y)
    if not back_soft():
        log('WARN 检测后未回到主界面, 下轮重试恢复')
    if unread:
        if notified:
            log('有未读私聊(已提醒), 等待已读')
            return notified
        if is_night():
            log_night_event('私聊', '检测到未读私聊')
            log_stat('私聊', '检出未读(夜间记日志)')
            log('有未读私聊, 已记夜间日志(夜间不推送)')
            return True
        if push_weixin('海岛私聊有未读消息, 请上线查看'):
            log_stat('私聊', '检出未读并推送')
            log('有未读私聊, 已推送提醒')
            return True
        log('有未读私聊, 直推失败, 下轮重试')
        return False
    if notified:
        log('未读私聊已清除')
    return False


def main():
    if '--stop' in sys.argv[1:]:
        return stop()
    if len(sys.argv) > 1:
        print('用法: python chat_watch.py [--stop]')
        return 1

    log('私聊未读监视启动, 每%d秒一轮(相位第%d秒)' % (TICK_PERIOD, TICK_PHASE))
    write_pid()
    notified = False
    try:
        while True:
            wait_tick()
            try:
                notified = check_round(notified)
            except Exception as e:
                log('本轮异常(继续监视): %r' % e)
    except KeyboardInterrupt:
        log('用户中断退出')
    finally:
        remove_pid()
    return 0


if __name__ == '__main__':
    sys.exit(main())
