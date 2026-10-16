# -*- coding: utf-8 -*-
"""停止游戏脚本 (单次执行)
流程: 游戏未运行 -> 直接报告
      运行中   -> am force-stop -> 等2秒复检
                  仍在运行 -> 再 force-stop 一次 -> 复检, 仍失败则报错
输出: 每步动作 + RESULT 汇总行
exit code: 0=已停止(含本来就未运行), 1=停止失败
"""
from game_lib import *
import sys

RECHECK_WAIT = 2                    # force-stop 后等待复检(秒)


def main():
    pid = game_pid()
    if not pid:
        print('NOT_RUNNING 游戏未运行, 无需停止')
        print('RESULT: 游戏未运行')
        return 0

    log('游戏运行中 (pid %s), 强制停止...' % pid)
    for i in (1, 2):
        adb.shell('am force-stop %s' % PKG)
        time.sleep(RECHECK_WAIT)
        if not game_pid():
            print('STOPPED 游戏已停止')
            print('RESULT: 游戏已停止')
            return 0
        log('停止后复检仍在运行, 重试 (%d/2)' % i)
    print('ERROR 停止失败 (进程仍在运行)')
    print('RESULT: 停止失败')
    return 1


if __name__ == '__main__':
    sys.exit(main())
