# -*- coding: utf-8 -*-
"""城战在线奖励自动领取 (每天 7 次, 传第几次)
流程: 主界面点"城战/世界"入口 -> 点"在线奖励"入口 -> 按次数点领取按钮
      -> 调同目录 check_main.py 回主界面
领取按钮 x 坐标按次数: 1:(208) 2/3/4:(398) 5:(488) 6:(678) 7:(868), y=1150
说明: 领取按钮点击完成即视为领取成功, 奖励到账以游戏内实际状态为准
claim_once(n) 为单次领取全流程(不含主界面前置校验), 供 claim_seq.py 复用
用法: python claim_online_reward.py <1-7>   (第几次领取)
exit code: 0=第n次领取成功且回主界面; 1=参数错误/不在主界面/进界面失败/回主界面失败
"""
import os
import subprocess
import sys

from game_lib import *

WORLD_X, WORLD_Y = 970, 1850            # 主界面"城战/世界"入口按钮
ONLINE_BTN_X, ONLINE_BTN_Y = 350, 145   # 城战/世界界面"在线奖励"入口按钮
CLAIM_Y = 1150                          # 领取按钮 y 坐标
CLAIM_X = {1: 208, 2: 398, 3: 398, 4: 398, 5: 488, 6: 678, 7: 868}
ENTER_WAIT = 2                           # 进城战/世界界面校验失败后复检等待(秒)


def back_to_main():
    """调同目录 check_main.py 恢复主界面, 返回 0成功/1失败"""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'check_main.py')
    print('恢复主界面...')
    code = subprocess.call([sys.executable, path])
    return 0 if code == 0 else 1


def claim_once(n):
    """单次领取全流程(进城战/世界->在线奖励->点领取->回主界面; 不含主界面前置校验)
    返回 (领取动作完成, 回主界面成功)"""
    log('进城战/世界界面')
    tap(WORLD_X, WORLD_Y)
    img = shot()
    if not has_citywar(img):
        time.sleep(ENTER_WAIT)
        img = shot()
    if not has_citywar(img):
        print('进入城战/世界界面失败')
        code = back_to_main()
        return (False, code == 0)
    log('进在线奖励界面')
    tap(ONLINE_BTN_X, ONLINE_BTN_Y)
    log('领取第%d次在线奖励' % n)
    tap(CLAIM_X[n], CLAIM_Y)
    code = back_to_main()
    return (True, code == 0)


def main():
    if len(sys.argv) != 2:
        print('用法: python claim_online_reward.py <1-7>   (第几次领取)')
        return 1
    try:
        n = int(sys.argv[1])
    except ValueError:
        print('用法: python claim_online_reward.py <1-7>   (第几次领取)')
        return 1
    if n not in CLAIM_X:
        print('ERROR 领取次数须为 1-7')
        return 1

    log('校验主界面')
    if not on_main(shot()):
        print('不在主界面, 尝试恢复')
        code = back_to_main()
        print('RESULT: 第%d次在线奖励领取不成功 不在主界面 回主界面=%s'
              % (n, '是' if code == 0 else '否'))
        return 1

    done, ok_main = claim_once(n)
    if done and ok_main:
        print('RESULT: 第%d次在线奖励领取成功 回主界面=是' % n)
        return 0
    if done:
        print('RESULT: 第%d次在线奖励领取成功 回主界面=否, 请运行 force_main.py 强制恢复' % n)
        return 1
    print('RESULT: 第%d次在线奖励领取不成功 进入城战/世界界面失败 回主界面=%s'
          % (n, '是' if ok_main else '否'))
    return 1


if __name__ == '__main__':
    sys.exit(main())
