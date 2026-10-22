# -*- coding: utf-8 -*-
"""联盟情报一键领取 (单次执行)
流程: 主界面 -> 联盟情报界面 -> 循环: OCR(250,870)-(590,930)命中"下次刷新时间"
      部分字样直接退出(无可领); 一键领取按钮可领则点击领取,
      过等级提升/结算界面回联盟情报界面再次检测, 直到不可领 -> 返回主界面
  一键领取判定: (690,1790) 橙色 = 可领; 领取后若 (500,270) 命中等级提升色,
  先点结算按钮进结算界面再回联盟情报界面, 否则等 3s 直接点回
输出: 每步动作 + RESULT 汇总行(等级提升时附加 等级提升N次), 机器可解析
不在主界面时自动调 check_main.py 恢复后继续(手动单跑友好)
exit code: 0=领取完成或无情报可领 1=不在主界面或恢复失败
"""
from game_lib import *
import os
import subprocess
import sys

INTEL_ENTRY = (60, 1400)      # 主界面联盟情报入口
CLAIM_PX = (690, 1790)        # 一键领取按钮判定点
CLAIM_REF = (47, 184, 255)    # 可一键领取参考色(橙)
BACK = (5, 1860)              # 联盟情报界面返回键(回主界面)
LV_PX = (500, 270)            # 等级提升界面判定点
LV_REF = (90, 236, 246)       # 等级提升界面参考色
SETTLE = (540, 1596)          # 结算/返回联盟情报按钮
SETTLE_WAIT = 3               # 结算界面停留等待(秒)
ENTER_WAIT = 2                # 进联盟情报界面等待(秒)
CLAIM_WAIT = 2                # 领取后画面切换等待(秒)
MAX_ROUNDS = 20               # 循环轮次上限(防异常死循环)
NEXT_BOX = (250, 870, 590, 930)  # "下次刷新时间"倒计时文本区域(无可领情报时出现)
NEXT_KEYS = '下次刷新时间'      # OCR 命中关键字
NEXT_HITS = 2                 # 最少命中字数(容许 OCR 部分识别)


def back_to_main():
    """调同目录 check_main.py 恢复主界面, 返回 0成功/1失败"""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'check_main.py')
    print('恢复主界面...')
    code = subprocess.call([sys.executable, path])
    return 0 if code == 0 else 1


def next_update_shown(img):
    """OCR 判(250,870)-(590,930)区域是否显示"下次刷新时间": 命中>=2字即真"""
    if img is None:
        return False
    x0, y0, x1, y1 = NEXT_BOX
    text = ocr_text(img[y0:y1, x0:x1])
    if not text:
        return False
    compact = text.replace(' ', '')
    return sum(1 for ch in NEXT_KEYS if ch in compact) >= NEXT_HITS


def main():
    ensure_device_free('claim_intel.py')
    img = shot()
    if not on_main(img):
        print('不在主界面, 尝试恢复')
        if back_to_main():
            print('RESULT: 联盟情报领取不成功 不在主界面 回主界面=否')
            return 1
        img = shot()
        if not on_main(img):
            print('RESULT: 联盟情报领取不成功 不在主界面 回主界面=否')
            return 1
        print('已恢复主界面, 继续领取流程')

    tap(*INTEL_ENTRY)
    time.sleep(ENTER_WAIT)
    rounds = 0
    levelups = 0
    while rounds < MAX_ROUNDS:
        img = shot()
        if next_update_shown(img):
            log('显示下次刷新时间, 无可领情报')
            break
        if not close(px(img, *CLAIM_PX), CLAIM_REF):
            break
        rounds += 1
        log('第%d轮一键领取' % rounds)
        tap(*CLAIM_PX)
        time.sleep(CLAIM_WAIT)
        img = shot()
        if close(px(img, *LV_PX), LV_REF):
            levelups += 1
            log('出现等级提升, 进结算界面')
            tap(*SETTLE)
            time.sleep(SETTLE_WAIT)
            tap(*SETTLE)
            time.sleep(ENTER_WAIT)
        else:
            time.sleep(SETTLE_WAIT)
            tap(*SETTLE)
            time.sleep(ENTER_WAIT)
    if rounds >= MAX_ROUNDS:
        log('达到轮次上限, 停止领取')

    tap(*BACK)
    time.sleep(1)
    if rounds:
        res = '联盟情报领取完成'
        if levelups:
            res += ' 等级提升%d次' % levelups
        print('RESULT: ' + res)
    else:
        print('RESULT: 无联盟情报可领')
    return 0


if __name__ == '__main__':
    sys.exit(main())
