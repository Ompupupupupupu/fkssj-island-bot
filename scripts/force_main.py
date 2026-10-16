# -*- coding: utf-8 -*-
"""强制返回主界面脚本 (check_main.py 恢复失败时使用)
流程: 已在主界面 -> 直接成功
      否则: 强制重启游戏 -> 轮询等待加载完成且停在主界面(上限180秒)
            超时(启动后停在弹窗/其他界面) -> 运行一次 check_main.py 恢复
      最终在主界面 -> 成功; 否则 -> 失败
输出: 每步动作
exit code: 0=已在/已回主界面, 1=强制恢复失败
"""
from game_lib import *
import sys, os, subprocess

PKG = 'com.gx.sw.qa.fkssj003.esj'   # 游戏包名
LOAD_TIMEOUT = 60                   # 重启后等待主界面上限(秒)
LOAD_POLL = 5                        # 轮询间隔(秒)


def main():
    if on_main(shot()):
        print('MAIN 已在主界面, 无需强制恢复')
        return 0

    log('强制重启游戏...')
    adb.shell('am force-stop %s' % PKG)
    time.sleep(2)
    adb.shell('monkey -p %s -c android.intent.category.LAUNCHER 1' % PKG)
    log('游戏已启动, 等待加载完成...')

    t0 = time.time()
    while time.time() - t0 < LOAD_TIMEOUT:
        time.sleep(LOAD_POLL)
        if on_main(shot()):
            print('RECOVERED 游戏重启后已回主界面')
            return 0
    log('等待超时, 启动后未直接停在主界面, 尝试 check_main.py 恢复')

    r = subprocess.call([sys.executable, '-u',
                         os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      'check_main.py')])
    if r == 0:
        print('RECOVERED 强制恢复完成, 已回主界面')
        return 0
    print('NOT_MAIN 强制恢复失败 (重启游戏后仍无法回主界面)')
    return 1


if __name__ == '__main__':
    sys.exit(main())
