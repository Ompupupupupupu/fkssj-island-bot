# -*- coding: utf-8 -*-
"""检查7种资源剩余数量 (只读, 不采集)
流程: 主界面 -> 资源界面 -> RapidOCR识别上限+各项 -> 返回主界面(带检测)
输出: 上限/阈值/各项数值与是否不足 + RESULT 汇总行(机器可解析)
不在主界面时自动调 check_main.py 恢复后继续(手动单跑友好)
exit code: 0=完成, 1=不在主界面, 2=上限OCR失败
"""
from game_lib import *
import os
import subprocess
import sys


def back_to_main():
    """调同目录 check_main.py 恢复主界面, 返回 0成功/1失败"""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'check_main.py')
    print('恢复主界面...')
    code = subprocess.call([sys.executable, path])
    return 0 if code == 0 else 1


def main():
    ensure_device_free('check_res.py')
    if not on_main(shot()):
        print('不在主界面, 尝试恢复')
        code = back_to_main()
        if code != 0:
            print('ERROR 恢复主界面失败, 终止资源检查')
            return 1
        log('已恢复主界面, 继续资源检查')
    log('主界面, 进资源界面')
    cap, vals, lack = scan_resources()
    if cap is None:
        print('ERROR 上限识别失败')
        return 2

    th = int(cap * CAP_RATIO)
    print('上限=%d 阈值=%d(%d%%)' % (cap, th, CAP_RATIO * 100))
    parts = []
    for name in RES_ITEMS:
        v = vals[name]
        if v is None:
            print('%s 识别失败' % name)
            parts.append('%s=?' % name)
            continue
        tag = '不足' if v < th else '充足'
        print('%s %d/%d (%d%%) %s' % (name, v, cap, round(v * 100 / cap), tag))
        parts.append('%s=%d' % (name, v))
    print('RESULT: 上限=%d %s 不足=%s' %
          (cap, ' '.join(parts), ','.join(lack) if lack else '无'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
