# -*- coding: utf-8 -*-
"""检查当前是否在游戏主界面; 不在则自动尝试返回主界面
主界面判定(on_main四重): nav_stage图标可见 + (300,255)非资源界面特征色
                         + 左上(310,220)-(385,255)无'城战'字样
                         + (65,1860)为主界面特征色
启动前置(闯关善后): PID文件(battle_run写)存在且进程枚举确认 battle_run 在跑
  -> 先杀其进程树(taskkill /T)并清 PID 文件, 再轮询善后战斗画面:
     战斗中点跳过(772,1725)快进, 出结算或回主界面即止, 超时交常规恢复兜底
  (双确认防止误杀: battle_run 正常退出时 finally 先删 PID 文件再调本脚本恢复,
   此时进程还活着但文件已删 -> 跳过终止分支)
自动返回:
  识别到"城战" -> 点"基地"按钮 (970,1850)
  其他界面     -> 点返回按钮 (5,1860)
  点击后复检; 第1次复检未回主界面 -> 第2次非城战点兜底按钮(10,1760)、
  城战则点"基地"按钮, 其后等3秒再检共2次, 每次未回主界面按界面类型点按钮(层层退回);
  全部尝试后等3秒做最终复检(最后一次点击生效不算失败)
输出: MAIN / 动作细节 / NOT_MAIN
exit code: 0=已在或已回主界面, 1=恢复失败
"""
from game_lib import *
import os
import subprocess
import sys

BASE_X, BASE_Y = 970, 1850       # 城战界面"基地"按钮
BACKBTN_X, BACKBTN_Y = 5, 1860   # 通用返回按钮
LAST_X, LAST_Y = 10, 1760        # 常规恢复全失败后的兜底按钮
RECOVER_WAIT = 3                  # 首次复检失败后再等秒数

# 闯关(battle_run)终止与战斗画面善后: 常量与判定同 battle_run.py
BATTLE_PID_FILE = os.path.join(os.environ.get('TEMP', '.'), 'fkssj_battle.pid')
SKIP_X, SKIP_Y = 772, 1725        # 战斗跳过按钮
RESULT_X, RESULT_Y = 1070, 420    # 结算判定采样像素点
WIN_BGR = (67, 25, 255)           # 胜利结算界面该点颜色
LOSE_BGR = (255, 121, 75)         # 失败结算界面该点颜色
COLOR_TOL = 40                    # 颜色判定每通道容差
BATTLE_WAIT_MAX = 90              # 战斗画面善后轮询上限(秒)
BATTLE_POLL = 2                   # 善后轮询间隔(秒)


def battle_settle_result(img):
    """采样结算色判定战斗结果(同 battle_run.check_result): 返回 'win'/'lose'/None"""
    if img is None:
        return None
    b, g, r = img[RESULT_Y, RESULT_X]
    for tag, ref in (('lose', LOSE_BGR), ('win', WIN_BGR)):
        if (abs(int(b) - ref[0]) <= COLOR_TOL and
                abs(int(g) - ref[1]) <= COLOR_TOL and
                abs(int(r) - ref[2]) <= COLOR_TOL):
            return tag
    return None


def stop_battle_run():
    """启动前置: 闯关在跑(PID文件存在 + 进程枚举确认双条件)则先终止并善后。
    返回 True=已终止(或善后完成), False=无需处理。
    杀进程树(taskkill /F /T, 覆盖在途 check_main 子进程)后轮询善后:
    战斗中点跳过快进 -> 出结算/回主界面即止, 超时交常规恢复兜底。
    双确认防误杀: battle_run 正常退出 finally 先删 PID 文件再调本脚本恢复,
    此时进程还在但文件已删 -> 不进终止分支。"""
    if not os.path.exists(BATTLE_PID_FILE):
        return False
    if find_device_holder() != 'battle_run.py':
        return False              # 进程枚举未确认(已死或枚举失败), 不终止
    print('检测到闯关进程在运行, 先终止...')
    pid = ''
    try:
        with open(BATTLE_PID_FILE) as f:
            pid = f.read().strip()
    except OSError:
        pass
    if pid.isdigit():
        subprocess.run(['taskkill', '/PID', pid, '/F', '/T'],
                       capture_output=True)
    else:
        print('WARN PID文件无效, 无法按PID终止')
    try:
        os.remove(BATTLE_PID_FILE)
    except OSError:
        pass
    t0 = time.time()
    while time.time() - t0 < BATTLE_WAIT_MAX:
        img = shot()
        if on_main(img):
            print('战斗画面已回主界面')
            return True
        if battle_settle_result(img):
            print('战斗已结算, 结算画面交常规恢复')
            return True
        print('战斗进行中, 点跳过按钮快进...')
        tap(SKIP_X, SKIP_Y)
        time.sleep(BATTLE_POLL)
    print('WARN 战斗画面善后超时, 交常规恢复兜底')
    return True


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
    use_last=True 且非城战点兜底按钮(第2次尝试用); 城战界面任何时候都点"基地"按钮"""
    img = shot()
    if on_main(img):
        print('RECOVERED 已回主界面 nav_score=%.2f' % nav_score(img))
        return True
    if use_last and not has_citywar(img):
        print('复检未回主界面, 点兜底按钮')
        tap(LAST_X, LAST_Y)
    else:
        recover_tap(img)
    return False


def check_recovered():
    """只读终检: 已回主界面打印 RECOVERED 并返回 True"""
    img = shot()
    if on_main(img):
        print('RECOVERED 已回主界面 nav_score=%.2f' % nav_score(img))
        return True
    return False


def main():
    stop_battle_run()
    img = shot()
    if on_main(img):
        print('MAIN nav_score=%.2f' % nav_score(img))
        return 0

    recover_tap(img)               # 第1次: 按界面类型点常规恢复按钮
    if try_recovered(use_last=True):   # 第2次: 复检未回主界面, 非城战点兜底/城战点"基地"
        return 0
    for i in (1, 2):               # 剩余次数: 每次等3秒, 未回主界面按界面类型点按钮
        time.sleep(RECOVER_WAIT)
        if try_recovered():
            return 0
    time.sleep(RECOVER_WAIT)       # 最终复检: 最后一次点击生效则不算失败
    if check_recovered():
        return 0
    print('NOT_MAIN 恢复失败')
    return 1


if __name__ == '__main__':
    sys.exit(main())
