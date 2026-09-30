import argparse
import os
import subprocess

APP_DIR = os.path.dirname(os.path.abspath(__file__))
STUBS_DIR = os.path.join(APP_DIR, 'packaging_stubs')
BUILD_DIR = os.path.join(APP_DIR, 'build')
DIST_DIR = os.path.join(APP_DIR, 'dist')
SPLASH_PNG = os.path.join(BUILD_DIR, 'splash.png')

MAIN_ENTRY = os.path.join(APP_DIR, 'main.py')
ONLINE_ENTRY = os.path.join(APP_DIR, 'main_online.py')
OFFLINE_ENTRY = os.path.join(APP_DIR, 'main_offline.py')

COMMON_COLLECT = ['jieba', 'bs4', 'pypdf', 'docx', 'requests']
ONLINE_COLLECT = ['deep_translator']
OFFLINE_COLLECT = ['argostranslate', 'ctranslate2', 'sentencepiece',
                   'sacremoses', 'minisbd']
BASE_EXCLUDE = ['torch', 'spacy', 'thinc', 'weasel']

VARIANTS = {
    'merged': {
        'name': '翻译对照工具',
        'entry': MAIN_ENTRY,
        'collect': COMMON_COLLECT + ONLINE_COLLECT + OFFLINE_COLLECT,
        'exclude': BASE_EXCLUDE,
        'paths': STUBS_DIR,
    },
    'online': {
        'name': '翻译对照工具_在线版',
        'entry': ONLINE_ENTRY,
        'collect': COMMON_COLLECT + ONLINE_COLLECT,
        'exclude': BASE_EXCLUDE + OFFLINE_COLLECT,
        'paths': None,
    },
    'offline': {
        'name': '翻译对照工具_离线版',
        'entry': OFFLINE_ENTRY,
        'collect': COMMON_COLLECT + OFFLINE_COLLECT,
        'exclude': BASE_EXCLUDE + ['deep_translator'],
        'paths': STUBS_DIR,
    },
}


def make_splash(path):
    from PIL import Image, ImageDraw, ImageFont
    w, h = 460, 260
    img = Image.new('RGB', (w, h), '#1E2A38')
    d = ImageDraw.Draw(img)

    def font(size, bold=False):
        names = ['msyhbd.ttc' if bold else 'msyh.ttc', 'msyh.ttc',
                 'simsun.ttc', 'arial.ttf']
        for name in names:
            try:
                return ImageFont.truetype(name, size)
            except Exception:
                continue
        return ImageFont.load_default()

    f1 = font(34, bold=True)
    f2 = font(16)
    t1 = '翻译对照工具'
    d.text(((w - d.textlength(t1, font=f1)) / 2, 88), t1,
           fill='#FFFFFF', font=f1)
    t2 = '正在启动，请稍候…'
    d.text(((w - d.textlength(t2, font=f2)) / 2, 152), t2,
           fill='#8FA3B8', font=f2)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path)


def build(variant):
    cfg = VARIANTS[variant]
    name = cfg['name']
    args = [
        'pyinstaller',
        '--noconfirm',
        '--clean',
        '--windowed',
        '--onefile',
        '--splash', SPLASH_PNG,
        '--name', name,
        '--distpath', DIST_DIR,
        '--workpath', BUILD_DIR,
        '--specpath', BUILD_DIR,
    ]
    if cfg['paths']:
        args += ['--paths', cfg['paths']]
    for pkg in cfg['collect']:
        args += ['--collect-all', pkg]
    for mod in cfg['exclude']:
        args += ['--exclude-module', mod]
    args.append(cfg['entry'])
    print('=' * 60)
    print('构建 {} 版本...'.format(variant))
    print('命令行:', ' '.join(args))
    print('=' * 60)
    subprocess.run(args, check=True)
    print('完成: {}'.format(os.path.join(DIST_DIR, name + '.exe')))


def main():
    parser = argparse.ArgumentParser(description='打包翻译对照工具为单文件 exe')
    parser.add_argument('variant', nargs='?', default='merged',
                        choices=['merged', 'online', 'offline'],
                        help='merged=在线+离线合并版(默认), '
                             'online=仅在线翻译, offline=仅离线翻译')
    args = parser.parse_args()
    make_splash(SPLASH_PNG)
    build(args.variant)


if __name__ == '__main__':
    main()
