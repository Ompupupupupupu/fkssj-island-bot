# -*- coding: utf-8 -*-
"""城战在线奖励后台编排: 依次领取每天 7 次在线奖励 (供定时任务后台启动)
流程: 校验主界面 -> 领第1次 -> 从上次领取完成点起算隔 INTERVALS[n] 秒领第n次(n=2..7)
      每次领取调用 claim_online_reward.claim_once(n); 某次失败也继续下一档(间隔照原值)
冷却说明: 间隔从领取完成点起算(>=游戏冷却), 与定时任务触发漂移无关
PID 文件 $TEMP/fkssj_claim_seq.pid 记录后台进程; --stop 按 PID 杀进程树停止
启动时同时创建结果待推送标记 $TEMP/fkssj_claim_seq_done.pending
  (结束后脚本自推结果: 夜间记夜间日志/日间 hermes 直推, 成功删除标记,
   日间直推失败保留标记由贸易/资源会话顺路兜底补推)
后台启动示例(日志重定向, 由 agent/cron 会话执行后立即返回, 不等待):
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File <launch_claim_seq.ps1>
  (启动器为只含 Start-Process 调本脚本的 .ps1, 模板见 references/battle.md;
   勿用 nohup——Hermes 终端会拒绝 shell 级后台包装, 命令不会执行)
总时长约 22 分钟(6次间隔共20分钟 + 7次领取动作各约30-60秒)
用法: python claim_seq.py            (启动编排, 供后台运行)
      python claim_seq.py --stop     (停止后台进程)
exit code: 0=7次领取全部成功 或 --stop 正常(含未在运行);
           1=不在主界面无法恢复 / 有领取失败 / PID文件读写异常
"""
import os
import subprocess
import sys

from game_lib import *
from claim_online_reward import back_to_main, claim_once

INTERVALS = {2: 60, 3: 120, 4: 180, 5: 240, 6: 300, 7: 300}   # 领完第n-1次后等多少秒领第n次
PID_FILE = os.path.join(os.environ.get('TEMP', '.'), 'fkssj_claim_seq.pid')
PENDING_FILE = os.path.join(os.environ.get('TEMP', '.'), 'fkssj_claim_seq_done.pending')   # 结果待推送标记


def write_pid():
    """写 PID 文件; 同时创建结果待推送标记(结束后脚本自推结果并删除; --stop 流程除外)"""
    try:
        with open(PID_FILE, 'w') as f:
            f.write(str(os.getpid()))
        open(PENDING_FILE, 'w').close()
    except Exception as e:
        print('WARN 写PID文件失败: %r' % e)


def remove_pid():
    try:
        os.remove(PID_FILE)
    except OSError:
        pass


def stop():
    """按 PID 文件停止后台领取进程(杀进程树, 避免在途 check_main 子进程残留)"""
    if not os.path.exists(PID_FILE):
        print('RESULT: 城战在线奖励后台领取未在运行')
        return 0
    try:
        with open(PID_FILE) as f:
            pid = f.read().strip()
        r = subprocess.run(['taskkill', '/PID', pid, '/F', '/T'],
                           capture_output=True)
    except Exception as e:
        print('RESULT: 城战在线奖励停止失败 %r' % e)
        return 1
    remove_pid()
    if r.returncode != 0:
        print('RESULT: 城战在线奖励后台领取未在运行(进程已不存在)')
        return 0
    print('RESULT: 城战在线奖励后台领取已停止, 过程详情见日志')
    return 0


def main():
    if '--stop' in sys.argv[1:]:
        return stop()
    if len(sys.argv) > 1:
        print('用法: python claim_seq.py [--stop]')
        return 1

    ensure_device_free('claim_seq.py')
    log('城战在线奖励后台编排启动')
    write_pid()
    img = shot()
    if not on_main(img):
        print('不在主界面, 尝试恢复')
        if back_to_main() != 0:
            remove_pid()
            print('RESULT: 城战在线奖励7次领取完成 成功0次 失败7次 回主界面=否')
            push_result('城战奖励', '海岛城战奖励7次领取未完成: 不在主界面无法恢复', PENDING_FILE)
            return 1

    ok = 0
    fail = 0
    for n in range(1, 8):
        if n >= 2:
            log('等待%d秒后领第%d次' % (INTERVALS[n], n))
            time.sleep(INTERVALS[n])
        done, ok_main = claim_once(n)
        if done:
            ok += 1
            log('第%d次领取完成 回主界面=%s' % (n, '是' if ok_main else '否'))
        else:
            fail += 1
            log('第%d次领取失败 回主界面=%s' % (n, '是' if ok_main else '否'))
    remove_pid()
    print('RESULT: 城战在线奖励7次领取完成 成功%d次 失败%d次' % (ok, fail))
    push_result('城战奖励', '海岛城战奖励7次领取完成 成功%d次 失败%d次' % (ok, fail), PENDING_FILE)
    return 0 if fail == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
