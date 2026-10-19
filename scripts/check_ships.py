# -*- coding: utf-8 -*-
"""检查三艘贸易船状态并对可交货的船自动交货, 之后进博物馆领人气币/收寻宝奖励 (单次执行)
流程: 主界面 -> 贸易界面 -> 逐船判定并处理 -> 返回主界面(贸易视角)
      -> 博物馆: 移展厅视角到最左 -> 有待领取人气币则领取;
         进寻宝界面数完成小队数并逐队收奖励 -> 有可派小队则扫描地图,
         从队首可派区域起逐区派遣小队直至派完 -> 返回博物馆 -> 返回主界面
  未回来色   -> 跳过
  已回来色   -> 点船收货 -> 点(500,1600)过结算 -> 隔1s点船交货 -> 弹窗判定 -> 复检
  货物不全色 -> 货已收(上次交货未成), 直接点船交货 -> 弹窗判定 -> 复检
弹窗判定: 交货后 0.5s 查"所需产品不足"弹窗(缺货交货被拒), 命中则点退出键回贸易页面
复检: 仍是货物不全色=交货失败(exit 2) / 变未回来色=交货成功
输出: 每步动作 + RESULT 汇总行(含 船N=.. 人气币=.. 寻宝奖励=.. 派出=.., 机器可解析)
不在主界面时自动调 check_main.py 恢复后继续(手动单跑友好)
exit code: 0=全部处理完(含未回来跳过) 1=不在主界面或未知状态 2=有船货物不足
"""
from game_lib import *
import cv2
import os
import subprocess
import sys

# 交货被拒检测: 点交货 0.5s 后截屏, (110,388) 为弹窗紫色标题栏 = 被"所需产品不足"
# 弹窗挡住(缺货交货被拒), 需点 (951,409) 弹窗退出键回贸易页面; 颜色不一致 = 交货
# 成功无弹窗, 无额外操作。参考色实测自缺货弹窗画面(两次独立截屏一致, 周边平坦)。
REJECT_CHECK_SEC = 0.5
REJECT_X, REJECT_Y = 110, 388
REJECT_BGR = (202, 99, 106)
REJECT_EXIT_X, REJECT_EXIT_Y = 951, 409

# 博物馆检查(贸易完成后): 人气币领取 + 寻宝小队奖励收取
# 参考色实测自截图: 人气币取 Screenshot_20261019-005846, 小队完成取
# Screenshot_20261019-005855; 反例(无)取 110424/110935, 特征色与反例色差均远超容差
MUSEUM_X, MUSEUM_Y = 150, 645        # 主界面(贸易视角)博物馆入口
COIN_PX = (570, 1290)               # 人气币气泡特征点(有待领取=橙)
COIN_REF = (95, 209, 255)
HUNT_PX = (866, 1737)               # 寻宝入口按钮(无论有无完成都进界面数小队)
TEAM_PTS = ((99, 1639), (306, 1639), (513, 1639))  # 寻宝界面小队完成检测三点
TEAM_REF = (125, 236, 51)           # 小队完成特征色(黄绿), 三点同一参考色
TEAM_CLAIM_X, TEAM_CLAIM_Y = 115, 1575   # 进入探险奖励结算(每轮同点)
REWARD_X, REWARD_Y = 538, 1538      # 结算界面领取奖励按钮
REWARD_EXIT_X, REWARD_EXIT_Y = 540, 1680  # 结算弹窗退出
MUS_WAIT = 2                        # 进博物馆/寻宝界面等待(秒)
MUS_BACK_X, MUS_BACK_Y = 5, 1860   # 博物馆界面返回键(回主界面)
MUS_SWIPE = 'input swipe 520 960 1060 960 600'  # 展厅中部向右拖540px(视角左移)
MUS_DIFF_TH = 5.0                   # 拖动前后画面平均差低于此值=已到最左(实测6次到位)

# 寻宝小队派出检测(领完奖励后): 可派小队>0才扫描地图可派区域, 逐区派遣直至小队派完或区域用尽
# 参考色实测自截图: 可派小队取 Screenshot_20261019-010000, 弹窗可/不可寻宝按钮取
# 142732/140435+142852, 正反例色差远超容差
SQUAD_PTS = ((214, 1490), (421, 1490), (628, 1490))  # 可派小队检测三点(寻宝界面)
SQUAD_REF = (87, 41, 255)             # 可派小队特征色(红)
AREAS = (('上1', (396, 428)), ('上2', (763, 561)), ('上3', (523, 780)),
         ('上4', (237, 968)), ('上5', (499, 1163)), ('上6', (847, 1038)),
         ('下1', (662, 1077)), ('下2', (252, 1096)), ('下3', (474, 1383)),
         ('下4', (852, 1452)))  # 寻宝区域点击顺序(上*=最上视角, 下*=最下视角)
AREA_PX = (667, 1554)                # 区域弹窗可寻宝判定点
AREA_REF_OK = (255, 129, 67)         # 可寻宝参考色(不可寻宝实测同为(255,208,199))
AREA_BACK_X, AREA_BACK_Y = 998, 295  # 区域弹窗退回按钮(回寻宝地图)
MAP_TOP_SWIPE = 'input swipe 540 960 540 1920 600'  # 中点向下拖960px(视角到最上)
MAP_BOT_SWIPE = 'input swipe 540 960 540 0 600'     # 中点向上拖960px(视角到最下)
AREA_WAIT = 2                        # 点区域后弹窗加载等待(秒)

# 小队派遣(队首区域起逐区派, 至可派小队派完): 区域弹窗"可寻宝"按钮即进派遣界面
# (复用 AREA_PX), 派遣界面选人确认后依次试小队槽位, 派出按钮可派则点击派出。
# 参考色实测自截图: 可派出取 Screenshot_20261019-144842, 不可派出取 144821
PICK_X, PICK_Y = 540, 894           # 派遣界面: 选择派遣人员
PICK_OK_X, PICK_OK_Y = 540, 1596    # 人员选择: 确认并回派遣界面
SLOT_PTS = ((705, 1410), (455, 1410), (205, 1410))  # 小队槽位(依次尝试)
SEND_PX = (670, 1535)               # 派出按钮判定点
SEND_REF_OK = (47, 184, 255)        # 可派出参考色(不可派出实测(125,213,47))


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
    time.sleep(REJECT_CHECK_SEC)
    img = shot()          # 先判交货后有无"所需产品不足"弹窗
    if close(px(img, REJECT_X, REJECT_Y), REJECT_BGR):
        print('船%d 交货被拒(所需产品不足), 退回贸易页面' % i)
        tap(REJECT_EXIT_X, REJECT_EXIT_Y)
        img = shot()      # 弹窗退回后的干净贸易页, 供复检与后续船判定
    else:
        time.sleep(RECHECK_SEC - REJECT_CHECK_SEC)  # 交货成功无弹窗, 补足原复检等待
        img = shot()      # 交货后界面刷新, 供复检与后续船判定
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


def probe_area(name, pt, found):
    """点开区域弹窗判定可寻宝并退回, 可寻宝则记入 found"""
    tap(*pt)
    time.sleep(AREA_WAIT)
    img = shot()
    ok = close(px(img, *AREA_PX), AREA_REF_OK)
    log('%s %s寻宝' % (name, '可' if ok else '不可'))
    if ok:
        found.append((name, pt))
    tap(AREA_BACK_X, AREA_BACK_Y)
    time.sleep(1)


def scan_hunt_areas():
    """扫描寻宝地图全部区域: 依次点开弹窗判定可寻宝,
    返回(区域名, 坐标)列表(按点击顺序记录, 后点击的在队首)"""
    found = []
    log('地图视角移到最上, 检查上6区')
    adb.shell(MAP_TOP_SWIPE)
    time.sleep(2)
    for name, pt in AREAS[:6]:
        probe_area(name, pt, found)
    log('地图视角移到最下, 检查下4区')
    adb.shell(MAP_BOT_SWIPE)
    time.sleep(2)
    for name, pt in AREAS[6:]:
        probe_area(name, pt, found)
    return found[::-1]


def dispatch_squads(areas, avail):
    """从队首区域起逐区派遣小队, 至 avail 支全部派出或区域用尽, 返回派出数。
    每区: 点区域 -> 弹窗"可寻宝"按钮进派遣界面 -> 选人确认 ->
    依次试小队槽位(派出按钮可派则点击派出) -> 退回寻宝界面"""
    sent = 0
    cur = '下'   # 扫描结束时视角在最下; 队列先下区后上区, 跨组时切视角
    for name, pt in areas:
        if sent >= avail:
            break
        if name[0] != cur:
            adb.shell(MAP_TOP_SWIPE if name[0] == '上' else MAP_BOT_SWIPE)
            cur = name[0]
            time.sleep(2)
        log('派遣区域%s' % name)
        tap(*pt)
        time.sleep(AREA_WAIT)
        tap(*AREA_PX)              # 弹窗"可寻宝"按钮进派遣界面
        time.sleep(AREA_WAIT)
        tap(PICK_X, PICK_Y)        # 选择派遣人员
        time.sleep(AREA_WAIT)
        tap(PICK_OK_X, PICK_OK_Y)  # 确认, 回派遣界面
        time.sleep(AREA_WAIT)
        done = False
        for slot in SLOT_PTS:
            tap(*slot)
            time.sleep(AREA_WAIT)
            img = shot()
            if close(px(img, *SEND_PX), SEND_REF_OK):
                tap(*SEND_PX)      # 派出小队, 回派遣界面
                time.sleep(AREA_WAIT)
                sent += 1
                done = True
                break
        log('%s %s' % (name, '已派出1支小队' if done else '无可派小队'))
        if done:
            tap(AREA_BACK_X, AREA_BACK_Y)  # 已在派遣界面, 一次回寻宝界面
            time.sleep(1)
        else:
            tap(AREA_BACK_X, AREA_BACK_Y)  # 先回派遣界面
            time.sleep(0.5)
            tap(AREA_BACK_X, AREA_BACK_Y)  # 再回寻宝界面
            time.sleep(1)
    return sent


def check_museum():
    """博物馆检查: 移展厅视角到最左领人气币 + 收寻宝小队奖励 + 派遣小队寻宝
    (前置=主界面贸易视角), 返回结果文本(结束回主界面)"""
    log('进博物馆界面')
    tap(MUSEUM_X, MUSEUM_Y)
    time.sleep(MUS_WAIT)
    img = shot()
    log('移动展厅视角到最左边')
    for _ in range(7):
        adb.shell(MUS_SWIPE)
        time.sleep(2)
        cur = shot()
        moved = cv2.absdiff(img, cur).mean() >= MUS_DIFF_TH
        img = cur
        if not moved:
            break
    coin = close(px(img, *COIN_PX), COIN_REF)
    if coin:
        log('有待领取人气币, 领取')
        tap(*COIN_PX)
        time.sleep(MUS_WAIT)
        img = shot()
    log('进寻宝界面')
    tap(*HUNT_PX)
    time.sleep(MUS_WAIT)
    img = shot()
    n = sum(1 for p in TEAM_PTS if close(px(img, *p), TEAM_REF))
    log('寻宝界面%d支小队完成' % n)
    for k in range(n):
        log('收取第%d支小队探险奖励' % (k + 1))
        tap(TEAM_CLAIM_X, TEAM_CLAIM_Y)
        time.sleep(5)
        tap(REWARD_X, REWARD_Y)
        time.sleep(3)
        tap(REWARD_EXIT_X, REWARD_EXIT_Y)
        time.sleep(1)
    img = shot()
    avail = sum(1 for p in SQUAD_PTS if close(px(img, *p), SQUAD_REF))
    log('可派出小队%d支' % avail)
    sent = 0
    if avail:
        areas = scan_hunt_areas()
        log('可寻宝区域(队首->队尾): %s' % (' '.join(n for n, _ in areas) if areas else '无'))
        if areas:
            sent = dispatch_squads(areas, avail)
            log('已派出小队%d支' % sent)
    log('返回博物馆, 再返回主界面')
    tap(MUS_BACK_X, MUS_BACK_Y)
    time.sleep(0.5)
    tap(MUS_BACK_X, MUS_BACK_Y)
    return '人气币=%s 寻宝奖励=%d支 派出=%d支' % ('已领' if coin else '无', n, sent)


def back_to_main():
    """调同目录 check_main.py 恢复主界面, 返回 0成功/1失败"""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'check_main.py')
    print('恢复主界面...')
    code = subprocess.call([sys.executable, path])
    return 0 if code == 0 else 1


def main():
    img = shot()
    if not on_main(img):
        print('不在主界面, 尝试恢复')
        code = back_to_main()
        if code != 0:
            print('ERROR 恢复主界面失败, 终止贸易检查')
            return 1
        log('已恢复主界面, 继续贸易检查')
        img = shot()
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
    log('已返回主界面(贸易视角)')

    results.append(check_museum())
    print('RESULT: ' + ' '.join(results))
    return worst


if __name__ == '__main__':
    sys.exit(main())
