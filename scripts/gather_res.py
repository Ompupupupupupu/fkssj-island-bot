# -*- coding: utf-8 -*-
"""资源采集脚本 (单次执行, 采集时长按剩余百分比自动判定, 采集后默认复查全部资源剩余)
用法: python gather_res.py <资源名> [--no-recheck]
  资源名: 鱼 塑料 木材 碎布 废金属 玻璃 海藻 (也接受序号1-7, 按此顺序)
  --no-recheck: 采集后不复查资源剩余
      (连续采集多种资源时逐个加此参数跳过复查, 全部采完由 check_res 统一复查)
流程: 主界面 -> 资源界面 -> OCR该资源剩余/上限定采集时长 -> 点"获取"按钮
      -> 点"前往"回主界面 -> 点(541,976) -> 0.5s后点(625,1115) 进采集界面
      -> 检测右下"自动"按钮是否旋转: 旋转=游戏已在自动采集; 否则点(962,1705)开启
      -> 按判定时长采集 -> 点(75,1735) -> 0.5s后点(540,1200) 回主界面
      -> 复检已在主界面 -> 复查全部资源剩余(同 check_res 逻辑), 附在 RESULT 行
      (带 --no-recheck 时跳过复查)
采集时长规则(按剩余百分比): >70% 采1分钟; 40%-70% 采3分钟; <40% 采5分钟
  (OCR 识别失败默认 3 分钟)
输出: 每步动作 + RESULT 行(默认含复查后的全资源剩余; --no-recheck 时仅采集完成)
exit code: 0=采集完成已回主界面 1=前置不满足/参数错误/退出后不在主界面
"""
from game_lib import *
import cv2
import sys

RES_NAMES = list(RES_ITEMS.keys())    # ['鱼','塑料','木材','碎布','废金属','玻璃','海藻']

# 游戏自带"自动采集": 采集界面右下"自动"按钮, 自动采集中按钮图标旋转, 未开启时静止
AUTO_BOX = (920, 1673, 1005, 1758)   # "自动"按钮检测区域(左上x0,y0 右下x1,y1)
AUTO_BTN_X, AUTO_BTN_Y = 962, 1705   # "自动"按钮点击位置
SPIN_FRAMES = 3                      # 旋转检测采样帧数
SPIN_INTERVAL = 0.6                  # 采样间隔(秒)
SPIN_DIFF_TH = 3.0                   # 相邻帧区域平均差>=此值=按钮在转


def is_spinning():
    """检测"自动"按钮区域是否旋转(=游戏正在自动采集):
    连续采样帧裁剪按钮区域做像素差分, 任一相邻帧对有差异=旋转中"""
    x0, y0, x1, y1 = AUTO_BOX
    prev = shot()[y0:y1, x0:x1]
    for _ in range(SPIN_FRAMES - 1):
        time.sleep(SPIN_INTERVAL)
        cur = shot()[y0:y1, x0:x1]
        if cv2.absdiff(prev, cur).mean() >= SPIN_DIFF_TH:
            return True
        prev = cur
    return False


def pick_name(arg):
    """参数 -> 资源名; 支持中文名或序号1-7, 无效返回 None"""
    if arg in RES_ITEMS:
        return arg
    if arg.isdigit() and 1 <= int(arg) <= len(RES_NAMES):
        return RES_NAMES[int(arg) - 1]
    return None


def decide_minutes(name, img):
    """资源界面截图 OCR 剩余与上限, 按百分比定采集时长:
    >70% -> 1分钟; 40%-70% -> 3分钟; <40% -> 5分钟; OCR失败默认3分钟"""
    cap = read_val(img, CAP_BOX)
    cur = read_val(img, RES_ITEMS[name][0])
    if not cap or cur is None:
        log('%s: 剩余识别失败, 默认采集 3 分钟' % name)
        return 3
    pct = round(cur * 100.0 / cap)
    if pct > 70:
        m = 1
    elif pct >= 40:
        m = 3
    else:
        m = 5
    log('%s: 剩余 %d/%d (%d%%), 采集 %d 分钟' % (name, cur, cap, pct, m))
    return m


def main():
    args = [a for a in sys.argv[1:] if a != '--no-recheck']
    no_recheck = len(args) != len(sys.argv) - 1
    if not args:
        print('ERROR 用法: python gather_res.py <鱼|塑料|木材|碎布|废金属|玻璃|海藻|1-7> [--no-recheck]')
        return 1
    name = pick_name(args[0])
    if name is None:
        print('ERROR 无效资源名: %r (可用: %s 或序号1-7)' %
              (args[0], '/'.join(RES_NAMES)))
        return 1

    img = shot()
    if not on_main(img):
        print('ERROR 不在主界面, 请先运行 check_main.py 确认/恢复')
        return 1

    bx, by = RES_ITEMS[name][1]
    log('主界面, 进资源界面')
    tap(RES_X, RES_Y)
    minutes = decide_minutes(name, shot())
    log('%s: 点"获取"按钮' % name)
    tap(bx, by)
    log('%s: 点"前往", 回主界面' % name)
    tap(GO_X, GO_Y)
    log('%s: 主界面采集入口第一步' % name)
    tap(MAIN1_X, MAIN1_Y)
    time.sleep(0.5)
    log('%s: 主界面采集入口第二步, 进入采集界面' % name)
    tap(MAIN2_X, MAIN2_Y)
    time.sleep(0.5)
    log('%s: 检测自动采集状态' % name)
    if is_spinning():
        log('%s: 已在自动采集' % name)
    else:
        log('%s: 未开启自动采集, 开启' % name)
        tap(AUTO_BTN_X, AUTO_BTN_Y)
    log('%s: 采集进行中, %d 分钟...' % (name, minutes))
    time.sleep(minutes * 60)
    log('%s: 采集结束, 退出' % name)
    tap(EXIT1_X, EXIT1_Y)
    time.sleep(0.5)
    tap(EXIT2_X, EXIT2_Y)
    ok = False
    for i in (1, 2, 3):              # 退出后画面切换可能未稳, 最多检3次
        ok = on_main(shot())
        if ok:
            break
        if i < 3:
            print('退出后未确认主界面, 等3秒重检 (%d/3)' % i)
            time.sleep(3)
    if not ok:
        print('RESULT: %s 采集失败 回主界面=否' % name)
        return 1
    if no_recheck:
        print('RESULT: %s 采集完成(%d分钟) 回主界面=是' % (name, minutes))
        return 0
    log('采集完成, 复查资源剩余...')
    cap, vals, lack = scan_resources()
    if cap is None:
        print('RESULT: %s 采集完成(%d分钟) 回主界面=是 复查=失败' % (name, minutes))
        return 0
    parts = ['%s=%s' % (n, vals[n] if vals[n] is not None else '?') for n in RES_ITEMS]
    print('RESULT: %s 采集完成(%d分钟) 回主界面=是 上限=%d %s 不足=%s' %
          (name, minutes, cap, ' '.join(parts), ','.join(lack) if lack else '无'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
