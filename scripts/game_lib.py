# -*- coding: utf-8 -*-
"""fkssj 游戏自动化共享库 (供 check_* 系列单次脚本调用)
从 status_check.py 提取的公共常量与函数; status_check.py 保持独立不受影响。
"""
import sys, os, time, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cv2
from pyadb import Adb
from rapidocr_onnxruntime import RapidOCR

# 路径自适应: 脚本在 <skill>/scripts/, 匹配模板在 <skill>/assets/, 截图写系统临时目录
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, 'assets')
SHOTS = os.path.join(tempfile.gettempdir(), 'fkssj_skill_shots')
os.makedirs(SHOTS, exist_ok=True)
SHOT = os.path.join(SHOTS, 'agent_check_last.png')

TAP_SLEEP = 1.5        # 点击后等界面切换(秒)
RECHECK_SEC = 1.0      # 交货后间隔多少秒再取色复检
COLOR_TOL = 10         # 颜色判定每通道容差
MATCH_TH = 0.80        # 主界面闯关图标匹配置信度阈值
CAP_RATIO = 0.70       # 剩余低于上限此比例则视为不足

CARGO_X, CARGO_Y = 75, 1115                            # 主界面贸易入口
BACK_X, BACK_Y = 1005, 200                             # 贸易界面返回主界面按钮
SETTLE_X, SETTLE_Y = 500, 1600                         # 收货结算画面返回贸易页面按钮
SHIP_POINTS = [(960, 640), (960, 1140), (960, 1640)]  # 三艘船标志像素
NOT_BACK_BGR = (255, 208, 199)   # 未回来标志颜色
BACK_BGR = (47, 183, 254)       # 已回来标志颜色
LACK_BGR = (254, 128, 67)       # 货物不全标志颜色

RES_X, RES_Y = 70, 195               # 主界面资源入口
RES_BACK_X, RES_BACK_Y = 1005, 200   # 资源界面返回主界面按钮
RES_MARK_X, RES_MARK_Y = 300, 255    # 资源界面特征像素(用于排除资源界面)
RES_MARK_BGR = (201, 99, 106)        # 资源界面(300,255)颜色; 主界面为(92,132,77)
MAIN_MARK_X, MAIN_MARK_Y = 65, 1860  # 主界面特征像素(左下角固定按钮)
MAIN_MARK_BGR = (243, 90, 105)       # 主界面该点颜色; 弹窗/其他界面为暗色(61,23,26)
CITYWAR_BOX = (310, 220, 385, 255)   # "城战"字样区域(主界面无此字样)
GO_X, GO_Y = 888, 824                # 资源界面"前往"按钮
MAIN1_X, MAIN1_Y = 541, 976          # 点"前往"回主界面后第一步(进采集界面)
MAIN2_X, MAIN2_Y = 625, 1115         # 0.5s后第二步, 进入采集界面
EXIT1_X, EXIT1_Y = 75, 1735          # 采集结束后第一步退出
EXIT2_X, EXIT2_Y = 540, 1200         # 0.5s后第二步, 回主界面
GATHER_SEC = 180                     # 采集固定时长(秒)
CAP_BOX = (675, 340, 800, 380)       # 上限数字裁剪框(所有资源共用)

# 资源: (剩余数量裁剪框x0,y0,x1,y1, 获取按钮x,y)
RES_ITEMS = {
    '鱼':    ((540,  340, 660,  380), (900,  430)),
    '塑料':  ((540,  510, 660,  550), (900,  600)),
    '木材':  ((540,  680, 660,  720), (900,  770)),
    '碎布':  ((540,  850, 660,  890), (900,  940)),
    '废金属': ((540, 1020, 660, 1060), (900, 1110)),
    '玻璃':  ((540, 1190, 660, 1230), (900, 1280)),
    '海藻':  ((540, 1360, 660, 1400), (900, 1450)),
}

NAV_STAGE = cv2.imread(os.path.join(ASSETS, 'nav_stage.png'))
if NAV_STAGE is None:
    raise SystemExit('模板缺失: nav_stage')
adb = Adb()
ocr_engine = RapidOCR()
PKG = 'com.gx.sw.qa.fkssj003.esj'   # 游戏包名


def game_pid():
    """游戏进程 pid 文本, 未运行返回 None"""
    out = adb.shell('pidof %s' % PKG).decode('utf-8', 'replace').strip()
    return out or None


def ocr_text(crop):
    """识别裁剪图中的文本: rec原尺寸 -> rec 3x放大 -> det 3x, 返回拼接文本(失败'')"""
    big = cv2.resize(crop, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    variants = [
        (crop, dict(use_det=False, use_cls=False)),
        (big,  dict(use_det=False, use_cls=False)),
        (big,  dict()),
    ]
    for im, kw in variants:
        try:
            res, _ = ocr_engine(im, **kw)
        except Exception:
            continue
        if not res:
            continue
        if kw.get('use_det', None) is False:
            text = ''.join(r[0] for r in res).strip()   # rec-only: [text, score]
        else:
            text = ''.join(r[1] for r in res).strip()   # det: [box, text, score]
        if text:
            return text
    return ''


def has_citywar(img):
    """左上(310,220)-(385,255)区域OCR是否含'城战'字样"""
    if img is None:
        return False
    x0, y0, x1, y1 = CITYWAR_BOX
    text = ocr_text(img[y0:y1, x0:x1])
    if not text:
        return False
    compact = text.replace(' ', '')
    return '城战' in compact or ('城' in compact and '战' in compact)


def log(msg):
    print('[%s] %s' % (time.strftime('%H:%M:%S'), msg))


def shot():
    time.sleep(0.3)
    adb.execout_to_file('screencap -p', SHOT)
    return cv2.imread(SHOT)


def px(img, x, y):
    return tuple(int(v) for v in img[y, x])


def close(c, ref):
    return all(abs(c[i] - ref[i]) <= COLOR_TOL for i in range(3))


def nav_score(img):
    """主界面闯关图标匹配置信度"""
    if img is None:
        return -1.0
    return cv2.matchTemplate(img, NAV_STAGE, cv2.TM_CCOEFF_NORMED).max()


def on_main(img):
    """检测是否在主界面: nav_stage图标可见 且 (300,255)非资源界面特征色
    且 左上无'城战'字样 且 (65,1860)为主界面特征色"""
    if img is None:
        return False
    if nav_score(img) < MATCH_TH:
        return False
    if close(px(img, RES_MARK_X, RES_MARK_Y), RES_MARK_BGR):
        return False
    if has_citywar(img):
        return False
    if not close(px(img, MAIN_MARK_X, MAIN_MARK_Y), MAIN_MARK_BGR):
        return False
    return True


def ship_state(c):
    """像素颜色 -> 船状态文本"""
    if close(c, NOT_BACK_BGR):
        return '未回来'
    if close(c, LACK_BGR):
        return '货物不全'
    if close(c, BACK_BGR):
        return '已回来'
    return '未知'


def tap(x, y):
    adb.shell('input tap %d %d' % (x, y))
    time.sleep(TAP_SLEEP)


def back_to_main_from_res():
    """从资源界面返回主界面(带检测, 防误点开礼包弹窗):
    已在主界面 -> 跳过点返回"""
    if on_main(shot()):
        log('已在主界面, 跳过点返回')
        return
    log('返回主界面')
    tap(RES_BACK_X, RES_BACK_Y)
    if on_main(shot()):
        return
    log('未回主界面 (返回后检测失败)')


def ocr_num(crop):
    """识别裁剪图中的数字: rec原尺寸 -> rec 3x放大 -> det 3x, 逐级降级"""
    big = cv2.resize(crop, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    variants = [
        (crop, dict(use_det=False, use_cls=False)),
        (big,  dict(use_det=False, use_cls=False)),
        (big,  dict()),
    ]
    for im, kw in variants:
        try:
            res, _ = ocr_engine(im, **kw)
        except Exception:
            continue
        if not res:
            continue
        if kw.get('use_det', None) is False:
            text = ''.join(r[0] for r in res).strip()   # rec-only: [text, score]
        else:
            text = ''.join(r[1] for r in res).strip()   # det: [box, text, score]
        digits = ''.join(ch for ch in text if ch.isdigit())
        if digits:
            return digits
    return ''


def read_val(img, box):
    """按裁剪框从截图识别整数, 失败返回 None"""
    x0, y0, x1, y1 = box
    text = ocr_num(img[y0:y1, x0:x1])
    return int(text) if text else None


def scan_resources():
    """进资源界面 OCR 上限+7项剩余并返回主界面; 调用前须在主界面
    成功: (上限, {资源名: 数值或None}, [不足名]); 上限识别失败: (None, None, None)"""
    tap(RES_X, RES_Y)
    img = shot()
    cap = read_val(img, CAP_BOX)
    if cap is None:
        back_to_main_from_res()
        return (None, None, None)
    th = int(cap * CAP_RATIO)
    vals, lack = {}, []
    for name in RES_ITEMS:
        v = read_val(img, RES_ITEMS[name][0])
        vals[name] = v
        if v is not None and v < th:
            lack.append(name)
    back_to_main_from_res()
    return (cap, vals, lack)
