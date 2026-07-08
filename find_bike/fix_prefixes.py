from pathlib import Path

folder = Path(r'F:\Github\PythonProjects\find_bike\new512')
for f in folder.glob('*'):
    if f.is_file():
        name = f.name
        while name.startswith('否_'):
            name = name[2:]
        new_name = '否_' + name
        if new_name != f.name:
            f.rename(f.with_name(new_name))
            print(f'{f.name} → {new_name}')
