# -*- coding: utf-8 -*-
"""自动闯关脚本 v4.1
流程: 主界面点"闯关"(贸易图标) -> 点"开战" -> 开战12秒后点(772,1725)跳过战斗看结果:
  - 结果判定: 采样截图 (1070,420) 处像素颜色
      胜利 BGR(67,25,255) / 失败 BGR(255,121,75), 每通道容差 40
  - 战斗失败: 直接点"再战一次"固定坐标(540,1520)
              连续 5 次失败 -> 告警退出"战力或阵型不对，无法继续闯关"
  - 战斗胜利: 点(775,1400)直接挑战下一关, 失败计数清零
  - 单场战斗超过 15 分钟无结算 -> 告警退出
  - 任何退出路径(连败/超时告警, 用户中断, 异常)结束后自动调同目录 check_main.py
    恢复主界面, 输出 RESULT 行(已回主界面/回主界面失败)
  - 启动时创建战果待推送标记 $TEMP/fkssj_battle_done.pending
    (结束后脚本自推战果: 夜间记夜间日志/日间 hermes 直推, 成功删除标记,
     日间直推失败保留标记由贸易/资源会话顺路兜底补推)
用法: python battle_run.py   (先手动打开游戏并停在主界面; 供后台启动, 见 SKILL.md)
      python battle_run.py --stop   (停止后台闯关进程)
Ctrl+C 随时中断, 打印统计。后台运行时用 --stop 停止, 统计看日志尾部。
"""
import sys, os, time, tempfile, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cv2
from pyadb import Adb
from game_lib import push_result

# 路径自适应: 脚本在 <skill>/scripts/, 匹配模板在 <skill>/assets/, 截图写系统临时目录
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ASSETS = os.path.join(ROOT, 'assets')
SHOTS = os.path.join(tempfile.gettempdir(), 'fkssj_skill_shots')
os.makedirs(SHOTS, exist_ok=True)
SHOT = os.path.join(SHOTS, 'auto_battle_last.png')
PID_FILE = os.path.join(os.environ.get('TEMP', '.'), 'fkssj_battle.pid')
PENDING_FILE = os.path.join(os.environ.get('TEMP', '.'), 'fkssj_battle_done.pending')   # 战果待推送标记

# 统计预初始化(模块级): 用户中断/异常退出时 finally 自推也能读到最新累计值
total_win = 0
total_lose = 0
t0 = time.time()

MAX_FAIL = 5          # 连续失败告警阈值
POLL_SEC = 2.0          # 轮询间隔(秒)
TAP_SLEEP = 1.5         # 点击后等界面切换(秒)
MAX_BATTLE_SEC = 900    # 单场战斗无结算超时(秒)
MATCH_TH = 0.80         # 模板匹配置信度阈值
SKIP_AFTER_SEC = 12     # 开战多少秒后点跳过
SKIP_X, SKIP_Y = 772, 1725      # 跳过战斗按钮坐标
RETRY_X, RETRY_Y = 540, 1520    # "再战一次"按钮固定坐标
NEXT_X, NEXT_Y = 775, 1400           # 胜利后点击直接挑战下一关
RESULT_X, RESULT_Y = 1070, 420        # 结果判定采样像素点
WIN_BGR = (67, 25, 255)               # 胜利结算界面该点颜色
LOSE_BGR = (255, 121, 75)             # 失败结算界面该点颜色
COLOR_TOL = 40                        # 颜色判定每通道容差

PATHS = {
    'nav_stage': os.path.join(ASSETS, 'nav_stage.png'),
    'btn_fight': os.path.join(ASSETS, 'btn_fight.png'),
}
TEMPLATES = {}
for k, p in PATHS.items():
    t = cv2.imread(p)
    if t is None:
        raise SystemExit('模板缺失: ' + k)
    TEMPLATES[k] = t
print('templates loaded: ' + ', '.join(
    '%s(%dx%d)' % (k, v.shape[1], v.shape[0]) for k, v in TEMPLATES.items()))

adb = Adb()


def shot():
    time.sleep(0.3)
    adb.execout_to_file('screencap -p', SHOT)
    return cv2.imread(SHOT)


def find(img, key):
    """全屏模板匹配, 返回 (score, cx, cy) 或 None"""
    if img is None:
        return None
    r = cv2.matchTemplate(img, TEMPLATES[key], cv2.TM_CCOEFF_NORMED)
    _, mx, _, loc = cv2.minMaxLoc(r)
    if mx < MATCH_TH:
        return None
    h, w = TEMPLATES[key].shape[:2]
    return mx, loc[0] + w // 2, loc[1] + h // 2


def check_result(img):
    """采样 (1070,420) 像素颜色判定战斗结果: 返回 'win' / 'lose' / None"""
    if img is None:
        return None
    b, g, r = img[RESULT_Y, RESULT_X]
    for tag, ref in (('lose', LOSE_BGR), ('win', WIN_BGR)):
        if (abs(int(b) - ref[0]) <= COLOR_TOL and
                abs(int(g) - ref[1]) <= COLOR_TOL and
                abs(int(r) - ref[2]) <= COLOR_TOL):
            return tag
    return None


def tap(cx, cy):
    adb.shell('input tap %d %d' % (cx, cy))
    time.sleep(TAP_SLEEP)


def alert(msg):
    """告警只打印到终端, 由 agent 把结果转告用户, 不弹窗"""
    print('[ALERT] ' + msg)


def write_pid():
    """把当前进程 PID 写入 PID 文件, 供 --stop 查找;
    同时创建战果待推送标记(长跑结束后脚本自推战果并删除; --stop 让位时由 agent 推送后删除)"""
    try:
        with open(PID_FILE, 'w') as f:
            f.write(str(os.getpid()))
        open(PENDING_FILE, 'w').close()
    except Exception as e:
        print('WARN 写PID文件失败: %r' % e)


def remove_pid():
    try:
        os.remove(PID_FILE)
    except OSError:
        pass


def stop():
    """按 PID 文件停止后台闯关进程(杀进程树, 避免在途 check_main 子进程残留)"""
    if not os.path.exists(PID_FILE):
        print('RESULT: 闯关未在运行')
        return 0
    try:
        with open(PID_FILE) as f:
            pid = f.read().strip()
        r = subprocess.run(['taskkill', '/PID', pid, '/F', '/T'],
                           capture_output=True)
    except Exception as e:
        print('RESULT: 闯关停止失败 %r' % e)
        return 1
    remove_pid()
    if r.returncode != 0:
        print('RESULT: 闯关未在运行(进程已不存在)')
        return 0
    print('RESULT: 闯关已停止, 统计见日志尾部')
    return 0


def back_to_main():
    """结束后调同目录 check_main.py 恢复主界面, 返回 0成功/1失败"""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'check_main.py')
    print('结束后恢复主界面...')
    code = subprocess.call([sys.executable, path])
    if code == 0:
        print('RESULT: 已回主界面')
        return 0
    print('RESULT: 回主界面失败, 请运行 force_main.py 强制恢复')
    return 1


def main():
    global total_win, total_lose, t0
    fail_count = 0
    total_win = 0
    total_lose = 0
    in_battle = False
    battle_start = 0
    skip_done = False
    t0 = time.time()
    print('开始自动闯关... (Ctrl+C 中断)')
    while True:
        img = shot()
        result = check_result(img)
        fight = find(img, 'btn_fight')
        stage = find(img, 'nav_stage')

        if result == 'lose':
            total_lose += 1
            fail_count += 1
            print('[%s] 战斗失败 #%d/%d' %
                  (time.strftime('%H:%M:%S'), fail_count, MAX_FAIL))
            if fail_count >= MAX_FAIL:
                alert('拼尽全力无法战胜……\n'
                      '(连续 %d 次失败, 胜 %d 负 %d, 用时 %.0f 分钟)' %
                      (MAX_FAIL, total_win, total_lose, (time.time() - t0) / 60))
                break
            print('[%s] 再战一次!!' % time.strftime('%H:%M:%S'))
            tap(RETRY_X, RETRY_Y)
            in_battle = True
            battle_start = time.time()
            skip_done = False

        elif result == 'win':
            total_win += 1
            fail_count = 0
            print('[%s] 战斗胜利! 已过 %d 关, 下一关!' %
                  (time.strftime('%H:%M:%S'), total_win))
            tap(NEXT_X, NEXT_Y)
            in_battle = True
            battle_start = time.time()
            skip_done = False

        elif fight:
            # 准备界面点"开战"; 胜利点下一关后若停在准备界面也在此处理
            print('[%s] 开始战斗!' % time.strftime('%H:%M:%S'))
            tap(fight[1], fight[2])
            in_battle = True
            battle_start = time.time()
            skip_done = False

        elif stage and not in_battle:
            print('[%s] 主界面, 准备战斗!' % time.strftime('%H:%M:%S'))
            tap(stage[1], stage[2])

        else:
            if in_battle:
                el = time.time() - battle_start
                if not skip_done and el >= SKIP_AFTER_SEC:
                    print('[%s] 战斗中……跳过战斗……' % time.strftime('%H:%M:%S'))
                    tap(SKIP_X, SKIP_Y)
                    skip_done = True
                elif time.time() - battle_start > MAX_BATTLE_SEC:
                    alert('单场战斗超时(%.0f分钟)未检测到结算, 退出\n'
                          '(胜 %d 负 %d)' % (MAX_BATTLE_SEC / 60, total_win, total_lose))
                    break
                elif el % 30 < POLL_SEC:
                    print('[%s] 战斗进行中... %d秒' % (time.strftime('%H:%M:%S'), el))
            else:
                print('[%s] 等待识别界面(无已知按钮)...' % time.strftime('%H:%M:%S'))
        time.sleep(POLL_SEC)

    print('结束: 胜 %d 负 %d, 用时 %.0f 分钟' %
          (total_win, total_lose, (time.time() - t0) / 60))


if __name__ == '__main__':
    if '--stop' in sys.argv[1:]:
        sys.exit(stop())
    code = 0
    write_pid()
    try:
        main()
    except KeyboardInterrupt:
        print('\n用户中断退出')
    except Exception as e:
        print('\n异常退出: %r' % e)
        code = 1
    finally:
        remove_pid()
        # 任何退出路径都先恢复主界面; 恢复失败或原异常 code 非零则 exit 1
        main_code = back_to_main() or code
        summary = '海岛闯关%s 共%d场 胜%d 负%d 用时%.0f分钟' % (
            '异常中断' if code else '结束',
            total_win + total_lose, total_win, total_lose, (time.time() - t0) / 60)
        push_result('闯关', summary, PENDING_FILE)
    sys.exit(main_code)
