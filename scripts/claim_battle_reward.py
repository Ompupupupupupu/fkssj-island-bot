# -*- coding: utf-8 -*-
"""闯关挂机奖励领取 (单次执行)
流程: 主界面 -> 点闯关入口进闯关界面 -> 点闯关奖励入口进奖励界面
      -> 清升级点: (445,1530) 与无升级点参考色一致 = 无升级点结束;
      不一致则点击一次, 0.5s 后复查, 直到无升级点(轮次上限防死循环)
      -> OCR 当前挂机小时数与挂机上限小时数
      -> 小时 >= 上限-1 或 >= 23(保底一天至少领一次) 则点领取奖励,
      等 5s 过结算画面回闯关界面, 再点返回键回主界面; 未达条件不领取回主界面
输出: 每步动作 + RESULT 汇总行, 机器可解析
不在主界面时自动调 check_main.py 恢复后继续(手动单跑友好)
exit code: 0=领取成功或未达条件不领取 1=不在主界面/恢复失败/挂机时间OCR失败
"""
from game_lib import *
import os
import subprocess
import sys

STAGE_ENTRY = (100, 1850)           # 主界面闯关入口
REWARD_ENTRY = (100, 1430)          # 闯关界面闯关奖励入口
UPGRADE_PX = (445, 1530)            # 升级点按钮判定点
UPGRADE_NONE_REF = (188, 188, 188)  # 无升级点参考色(奖励界面参考截屏提取)
UPGRADE_GAP = 0.5                   # 升级点点击后复查间隔(秒)
MAX_UPGRADES = 30                   # 升级点点击轮次上限(防死循环)
CURR_BOX = (365, 1345, 445, 1405)  # 当前挂机小时数 OCR 框
MAX_BOX = (720, 1365, 765, 1395)    # 挂机时长上限(小时) OCR 框
CLAIM_PX = (765, 1525)              # 领取奖励按钮
SETTLE = (540, 1596)                # 领取后返回闯关界面按钮
BACK = (5, 1860)                    # 闯关界面返回键(回主界面)
STAGE_WAIT = 2                      # 进闯关界面等待(秒)
REWARD_WAIT = 2                     # 进奖励界面等待(秒)
CLAIM_WAIT = 5                      # 领取后动画/结算等待(秒)
SETTLE_WAIT = 1                     # 回闯关界面后等待(秒)
MIN_HOUR = 23                       # 保底领取小时(一天至少领一次)


def back_to_main():
    """调同目录 check_main.py 恢复主界面, 返回 0成功/1失败"""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'check_main.py')
    print('恢复主界面...')
    code = subprocess.call([sys.executable, path])
    return 0 if code == 0 else 1


def quick_tap(x, y, wait):
    """快速点击: 自控等待(升级点 0.5s 节奏, 不走 tap 的 1.5s 长等待)"""
    adb.shell('input tap %d %d' % (x, y))
    time.sleep(wait)


def clear_upgrades():
    """清升级点: (445,1530) 与无升级点参考色一致 = 无升级点, 结束;
    不一致则点击一次, 0.5s 后复查, 直到无升级点; 返回点击次数"""
    n = 0
    while n < MAX_UPGRADES:
        img = shot()
        if close(px(img, *UPGRADE_PX), UPGRADE_NONE_REF):
            return n
        n += 1
        log('点击升级点 #%d' % n)
        quick_tap(*UPGRADE_PX, UPGRADE_GAP)
    log('达到升级点轮次上限, 停止点击')
    return n


def can_claim(cur, tmax):
    """领取条件: 当前小时 >= 上限-1 或 >= 保底小时(一天至少领一次);
    返回 True=应领 / False=未达 / None=OCR 不足以为判
    (当前小时无效, 或上限无效且未达保底)"""
    if cur is None:
        return None
    if cur >= MIN_HOUR:
        return True
    if tmax is None:
        return None
    return cur >= tmax - 1


def main():
    ensure_device_free('claim_battle_reward.py')
    img = shot()
    if not on_main(img):
        print('不在主界面, 尝试恢复')
        if back_to_main():
            print('RESULT: 闯关奖励领取不成功 不在主界面 回主界面=否')
            return 1
        img = shot()
        if not on_main(img):
            print('RESULT: 闯关奖励领取不成功 不在主界面 回主界面=否')
            return 1
        print('已恢复主界面, 继续领取流程')

    tap(*STAGE_ENTRY)
    time.sleep(STAGE_WAIT)
    tap(*REWARD_ENTRY)
    time.sleep(REWARD_WAIT)

    ups = clear_upgrades()
    if ups:
        log('升级点已清完, 共%d次' % ups)
    else:
        log('无升级点')

    img = shot()
    cur = read_val(img, CURR_BOX)
    tmax = read_val(img, MAX_BOX)
    log('OCR 当前挂机小时=%r 上限小时=%r' % (cur, tmax))
    verdict = can_claim(cur, tmax)
    if verdict is None:
        print('RESULT: 闯关奖励领取不成功 挂机时间OCR失败')
        return 1

    if verdict:
        log('达到领取条件, 领取奖励')
        tap(*CLAIM_PX)
        time.sleep(CLAIM_WAIT)
        tap(*SETTLE)
        time.sleep(SETTLE_WAIT)
        tap(*BACK)
        time.sleep(1)
        print('RESULT: 闯关奖励领取成功')
        return 0

    # 未达条件: 不领取, 回主界面
    tap(*BACK)
    time.sleep(1)
    if not on_main(shot()):
        if back_to_main():
            print('RESULT: 闯关奖励领取不成功 不在主界面 回主界面=否')
            return 1
    print('RESULT: 闯关奖励未领取 挂机时长不足')
    return 0


if __name__ == '__main__':
    sys.exit(main())
