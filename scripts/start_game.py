# -*- coding: utf-8 -*-
"""启动游戏脚本 (单次执行; 启动流程参考 force_main.py)
流程: 游戏已在运行 -> 报告状态(不重启), 顺带报告是否在主界面
      未运行     -> monkey 冷启动 -> 轮询等待加载完成停主界面(上限60秒)
      超时:
        进程已起但未停主界面(弹窗/加载慢) -> 运行一次 check_main.py 恢复
        进程未起(包名错/模拟器异常)       -> 启动失败
输出: 每步动作 + RESULT 汇总行
exit code: 0=游戏运行中(已在运行或已启动, 不要求必须在主界面), 1=启动失败
"""
from game_lib import *
import sys, os, subprocess

LOAD_TIMEOUT = 60                   # 启动后等待主界面上限(秒)
LOAD_POLL = 5                       # 轮询间隔(秒)


def main():
    ensure_device_free('start_game.py')
    pid = game_pid()
    if pid:
        log('游戏已在运行 (pid %s), 不重启' % pid)
        on = on_main(shot())
        print('RESULT: 游戏运行中 主界面=%s' % ('是' if on else '否'))
        if not on:
            print('提示: 不在主界面可用 check_main.py 恢复')
        return 0

    log('启动游戏...')
    adb.shell('monkey -p %s -c android.intent.category.LAUNCHER 1' % PKG)
    log('游戏已启动, 等待加载完成...')

    t0 = time.time()
    while time.time() - t0 < LOAD_TIMEOUT:
        time.sleep(LOAD_POLL)
        if on_main(shot()):
            print('STARTED 游戏已启动, 已停主界面')
            print('RESULT: 游戏已启动 主界面=是')
            return 0

    pid = game_pid()
    if not pid:
        print('NOT_STARTED 启动失败 (游戏进程未起来)')
        print('RESULT: 启动失败 主界面=否')
        return 1

    log('等待超时, 游戏进程在但未停主界面, 尝试 check_main.py 恢复')
    r = subprocess.call([sys.executable, '-u',
                         os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      'check_main.py')])
    if r == 0:
        print('STARTED 游戏已启动, 恢复后已回主界面')
        print('RESULT: 游戏已启动 主界面=是')
        return 0
    print('NOT_STARTED 启动失败 (游戏无法回主界面)')
    print('RESULT: 启动失败 主界面=否')
    return 1


if __name__ == '__main__':
    sys.exit(main())
