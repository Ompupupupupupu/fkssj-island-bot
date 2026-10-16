# -*- coding: utf-8 -*-
"""检查三艘贸易船状态并对可交货的船自动交货 (单次执行)
流程: 主界面 -> 贸易界面 -> 逐船判定并处理 -> 返回主界面
  未回来色   -> 跳过
  已回来色   -> 点船收货 -> 点(500,1600)过结算 -> 隔1s点船交货 -> 复检
  货物不全色 -> 货已收(上次交货未成), 直接点船交货 -> 复检
复检: 仍是货物不全色=交货失败(exit 2) / 变未回来色=交货成功
输出: 每步动作 + RESULT 汇总行(机器可解析)
exit code: 0=全部处理完(含未回来跳过) 1=不在主界面或未知状态 2=有船货物不足
"""
from game_lib import *
import sys


def handle_ship(i, img):
    """判定船i状态并执行对应动作, 返回 (结果文本, exit贡献码, 刷新后的截图)"""
    x, y = SHIP_POINTS[i - 1]
    c = px(img, x, y)
    s = ship_state(c)
    if s == '未回来':
        print('船%d 未回来, 跳过' % i)
        return '未回来', 0, img
    if s == '未知':
        print('船%d 未知状态 BGR%s, 不操作' % (i, c))
        return '未知', 1, img
    if s == '已回来':
        print('船%d 已回来, 点击收货' % i)
        tap(x, y)                        # 收货 -> 弹出收货结算画面
        print('船%d 收货结算, 回贸易页面' % i)
        tap(SETTLE_X, SETTLE_Y)
        time.sleep(RECHECK_SEC)
        print('船%d 完成交货' % i)
        tap(x, y)                        # 交货
    else:  # 货物不全
        print('船%d 货物不全遗留(货已收), 尝试交货' % i)
        tap(x, y)                        # 直接交货, 无需结算
    time.sleep(RECHECK_SEC)
    img = shot()          # 交货后界面刷新, 供后续船判定
    c2 = px(img, x, y)
    s2 = ship_state(c2)
    if s2 == '货物不全':
        print('船%d 货物不足, 无法交货!' % i)
        return '交货失败(货物不足)', 2, img
    if s2 == '未回来':
        print('船%d 交货完成' % i)
        return '交货完成', 0, img
    print('船%d 交货后未知状态 BGR%s' % (i, c2))
    return '交货后未知', 1, img


def main():
    img = shot()
    if not on_main(img):
        print('ERROR 不在主界面, 请先运行 check_main.py 确认')
        return 1
    log('主界面, 进贸易界面')
    tap(CARGO_X, CARGO_Y)

    img = shot()
    results = []
    worst = 0
    for i in (1, 2, 3):
        txt, code, img = handle_ship(i, img)
        results.append('船%d=%s' % (i, txt))
        if code == 1:
            worst = 1
        elif code == 2 and worst == 0:
            worst = 2

    tap(BACK_X, BACK_Y)
    log('已返回主界面')
    print('RESULT: ' + ' '.join(results))
    return worst


if __name__ == '__main__':
    sys.exit(main())
