# -*- coding: utf-8 -*-
"""雷电模拟器基础配置检查/修正 (平板版: 配置分辨率 1920x1080, DPI 280)
检查实例配置 leidian<instance>.config 的 advancedSettings.resolution(宽1920高1080)
与 resolutionDpi(280):
  符合 -> exit 0
  不符合 -> 自动改写配置文件; 模拟器未运行 exit 0(下次启动生效),
            模拟器运行中 exit 2(需重启模拟器生效)
雷电安装目录定位(按优先级):
  1. 命令行参数 --ld-dir <路径>
  2. 环境变量 FKSSJ_LD_DIR
  3. 自动探测候选列表(第一个含 vms\\config 子目录的生效)
  全部未命中 -> ERROR 提示用 --ld-dir, exit 1
说明:
  - 1920x1080 为雷电平板版配置值(横屏存储), 竖屏显示时 adb 截图为 1080x1920,
    本项目全部脚本坐标基于该竖屏截图
  - 模拟器运行中改写配置可能在其退出时被内存态覆盖; 重启后重跑本脚本,
    若仍不符则先关闭模拟器再跑本脚本修正, 然后启动
用法: python setup_emulator.py [--ld-dir <雷电安装目录>] [--instance <实例名>]
  (--instance 默认 leidian0)
exit code: 0=配置符合(或已修正且模拟器未运行) 1=读写失败或安装目录未找到 2=已修正需重启模拟器
"""
import json
import os
import subprocess
import sys

# 自动探测候选: 常见默认安装位置, 未命中需 --ld-dir 显式指定
LD_CANDIDATES = [
    r'C:\LDPlayer9',
    r'D:\LDPlayer9',
    r'C:\Program Files\LDPlayer9',
]
WANT_W, WANT_H, WANT_DPI = 1920, 1080, 280     # 平板版预设


def parse_args(argv):
    """解析 --ld-dir / --instance (空格与=两种形式), 返回 (ld_dir, instance)"""
    ld_dir, instance = None, 'leidian0'
    i = 1
    while i < len(argv):
        a = argv[i]
        if a == '--ld-dir' and i + 1 < len(argv):
            ld_dir = argv[i + 1]
            i += 2
        elif a.startswith('--ld-dir='):
            ld_dir = a.split('=', 1)[1]
            i += 1
        elif a == '--instance' and i + 1 < len(argv):
            instance = argv[i + 1]
            i += 2
        elif a.startswith('--instance='):
            instance = a.split('=', 1)[1]
            i += 1
        else:
            print('ERROR 未知参数: %s' % a)
            i += 1
    return ld_dir, instance


def locate_ld_dir(explicit):
    """定位雷电安装目录: 显式参数 > 环境变量 > 候选探测; 未命中返回 None"""
    if explicit:
        return explicit
    env = os.environ.get('FKSSJ_LD_DIR')
    if env:
        return env
    for d in LD_CANDIDATES:
        if os.path.isdir(os.path.join(d, 'vms', 'config')):
            return d
    return None


def emulator_running():
    """雷电9 主窗口进程 dnplayer.exe 是否在运行"""
    try:
        out = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq dnplayer.exe'],
                             capture_output=True).stdout
        return b'dnplayer.exe' in out.lower()
    except Exception:
        return False


def main():
    ld_dir, instance = parse_args(sys.argv)
    ld_dir = locate_ld_dir(ld_dir)
    if not ld_dir:
        print('ERROR 未找到雷电模拟器安装目录, 请用 --ld-dir <路径> 指定')
        return 1
    config = os.path.join(ld_dir, 'vms', 'config', '%s.config' % instance)
    print('使用安装目录: %s (实例 %s)' % (ld_dir, instance))
    if not os.path.exists(config):
        print('ERROR 配置文件不存在: %s' % config)
        return 1
    try:
        with open(config, encoding='utf-8') as f:
            cfg = json.load(f)
    except Exception as e:
        print('ERROR 配置解析失败: %r' % e)
        return 1

    adv = cfg.get('advancedSettings', {})
    res = adv.get('resolution', {})
    w, h, dpi = res.get('width'), res.get('height'), adv.get('resolutionDpi')
    running = emulator_running()

    if w == WANT_W and h == WANT_H and dpi == WANT_DPI:
        print('RESULT: 模拟器配置符合 平板版分辨率%dx%d DPI%d 模拟器运行=%s'
              % (WANT_W, WANT_H, WANT_DPI, '是' if running else '否'))
        return 0

    print('当前配置: 分辨率=%sx%s DPI=%s (要求 %dx%d DPI%d), 修正中...'
          % (w, h, dpi, WANT_W, WANT_H, WANT_DPI))
    adv = cfg.setdefault('advancedSettings', {})
    adv['resolution'] = {'width': WANT_W, 'height': WANT_H}
    adv['resolutionDpi'] = WANT_DPI
    try:
        with open(config, 'w', encoding='utf-8') as f:
            json.dump(cfg, f, ensure_ascii=False, indent=4)
            f.write('\n')
    except Exception as e:
        print('ERROR 配置写入失败: %r' % e)
        return 1

    if running:
        print('RESULT: 配置已修正 分辨率%dx%d DPI%d 模拟器运行中, 重启模拟器后生效'
              % (WANT_W, WANT_H, WANT_DPI))
        return 2
    print('RESULT: 配置已修正 分辨率%dx%d DPI%d 模拟器未运行, 下次启动生效'
          % (WANT_W, WANT_H, WANT_DPI))
    return 0


if __name__ == '__main__':
    sys.exit(main())
