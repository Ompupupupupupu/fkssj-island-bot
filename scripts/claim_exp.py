# -*- coding: utf-8 -*-
"""经验自动领取
统一领取各建筑经验(训练营/冶炼厂/海兽训练营等, 均在锻造厂视角可见):
主界面进装备锻造界面 -> 有弹窗则关闭 -> 按返回键回到以锻造厂为中心的主界面
-> 检测经验气泡(两点均为橙色) -> 有则点击领取, 结束时就在主界面无需恢复
无经验判定: 气泡特征点颜色不是橙色(无经验时两点为灰白/灰绿等背景色)
用法: python claim_exp.py
exit code: 0=领取成功或无经验可领(均在主界面); 1=不在主界面或恢复失败
"""
import os
import subprocess
import sys

from game_lib import *

FORGE_X, FORGE_Y = 72, 976          # 主界面装备锻造入口
POPUP_PX = (730, 270)               # 锻造界面弹窗特征点
POPUP_REF = (239, 151, 255)         # 弹窗特征色 BGR(参考截图 Screenshot_20261019-012819)
POPUP_CLOSE_X, POPUP_CLOSE_Y = 540, 1680   # 弹窗关闭按钮
BACK_X, BACK_Y = 5, 1860            # 返回键
EXP_PX_A = (626, 404)               # 经验气泡特征点A
EXP_PX_B = (908, 566)               # 经验气泡特征点B
EXP_REF = (95, 209, 255)            # 经验气泡橙色 BGR(参考截图 Screenshot_20261019-103801)
ENTER_WAIT = 2                      # 进界面/关弹窗/切视角后的等待(秒)


def back_to_main():
    """调同目录 check_main.py 恢复主界面, 返回 0成功/1失败"""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'check_main.py')
    print('恢复主界面...')
    code = subprocess.call([sys.executable, path])
    return 0 if code == 0 else 1


def has_exp(img):
    """经验气泡两点均为橙色 = 有待领取经验"""
    return (close(px(img, *EXP_PX_A), EXP_REF)
            and close(px(img, *EXP_PX_B), EXP_REF))


def main():
    log('校验主界面')
    if not on_main(shot()):
        print('不在主界面, 尝试恢复')
        code = back_to_main()
        if code != 0:
            print('RESULT: 经验领取不成功 不在主界面 回主界面=否')
            return 1
        log('已恢复主界面, 继续领取流程')

    log('进入装备锻造界面')
    tap(FORGE_X, FORGE_Y)
    time.sleep(ENTER_WAIT)
    img = shot()
    if close(px(img, *POPUP_PX), POPUP_REF):
        log('检测到弹窗, 关闭后继续')
        tap(POPUP_CLOSE_X, POPUP_CLOSE_Y)
        time.sleep(ENTER_WAIT)

    log('返回锻造厂视角')
    tap(BACK_X, BACK_Y)
    time.sleep(ENTER_WAIT)

    img = shot()
    if has_exp(img):
        log('检测到待领取经验, 领取')
        tap(*EXP_PX_A)
        time.sleep(ENTER_WAIT)
        print('RESULT: 经验领取成功')
        return 0
    print('RESULT: 无经验可领')
    return 0


if __name__ == '__main__':
    sys.exit(main())
