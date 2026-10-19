# -*- coding: utf-8 -*-
"""游戏运行状态只读探测 (不截图/不点按/不依赖 game_lib 的 OCR 等重资源)
检测阶梯: adb server 连不上或无设备 -> 模拟器未启动
          设备在但游戏进程不在     -> 模拟器已启动 游戏未运行
          游戏进程在               -> 游戏运行中
供定时任务执行前探测(游戏未运行时询问用户是否启动), 也可手动查询游戏状态。
输出: RESULT 汇总行
exit code: 0=游戏运行中; 2=需用户行动(模拟器未启动或游戏未运行); 1=检测异常
"""
import sys
from pyadb import Adb

PKG = 'com.gx.sw.qa.fkssj003.esj'   # 游戏包名, 与 game_lib.py 保持同步维护


def main():
    try:
        adb = Adb()
    except Exception:
        print('RESULT: 模拟器未启动')
        return 2
    try:
        out = adb.shell('pidof %s' % PKG).decode('utf-8', 'replace').strip()
    except Exception as e:
        print('RESULT: 检测异常 %r' % e)
        return 1
    if out:
        print('RESULT: 游戏运行中')
        return 0
    print('RESULT: 模拟器已启动 游戏未运行')
    return 2


if __name__ == '__main__':
    sys.exit(main())
