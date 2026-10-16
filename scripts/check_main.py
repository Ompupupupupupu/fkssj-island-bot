# -*- coding: utf-8 -*-
"""检查当前是否在游戏主界面; 不在则自动尝试返回主界面
主界面判定(on_main四重): nav_stage图标可见 + (300,255)非资源界面特征色
                         + 左上(310,220)-(385,255)无'城战'字样
                         + (65,1860)为主界面特征色
自动返回:
  识别到"城战" -> 点"基地"按钮 (970,1850)
  其他界面     -> 点返回按钮 (5,1860)
  点击后复检; 第1次复检未回主界面 -> 第2次改点兜底按钮(10,1760),
  其后等3秒再检共2次, 每次未回主界面点返回按钮(层层退回)
输出: MAIN / 动作细节 / NOT_MAIN
exit code: 0=已在或已回主界面, 1=恢复失败
"""
from game_lib import *
import sys

BASE_X, BASE_Y = 970, 1850       # 城战界面"基地"按钮
BACKBTN_X, BACKBTN_Y = 5, 1860   # 通用返回按钮
LAST_X, LAST_Y = 10, 1760        # 常规恢复全失败后的兜底按钮
RECOVER_WAIT = 3                  # 首次复检失败后再等秒数


def recover_tap(img):
    """按当前界面类型点恢复按钮: 城战->基地按钮, 其他->返回按钮"""
    if has_citywar(img):
        print('城战界面, 点"基地"按钮返回')
        tap(BASE_X, BASE_Y)
    else:
        print('非主界面(非城战), 点返回按钮')
        tap(BACKBTN_X, BACKBTN_Y)


def try_recovered(use_last=False):
    """复检并按需再点恢复按钮: 已回主界面True; 否则点一次恢复按钮后False
    use_last=True 点兜底按钮(第2次尝试用); 否则按界面类型点常规按钮(层层退回)"""
    img = shot()
    if on_main(img):
        print('RECOVERED 已回主界面 nav_score=%.2f' % nav_score(img))
        return True
    if use_last:
        print('复检未回主界面, 点兜底按钮')
        tap(LAST_X, LAST_Y)
    else:
        recover_tap(img)
    return False


def main():
    img = shot()
    if on_main(img):
        print('MAIN nav_score=%.2f' % nav_score(img))
        return 0

    recover_tap(img)               # 第1次: 按界面类型点常规恢复按钮
    if try_recovered(use_last=True):   # 第2次: 复检未回主界面点兜底按钮
        return 0
    for i in (1, 2):               # 剩余次数: 每次等3秒, 未回主界面点返回按钮
        time.sleep(RECOVER_WAIT)
        if try_recovered():
            return 0
    print('NOT_MAIN 恢复失败')
    return 1


if __name__ == '__main__':
    sys.exit(main())
