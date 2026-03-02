import os

path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'main.py')
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

if 'load-display p3tinydisplay' in content:
    print('Already patched')
else:
    # Insert loadPrcFileData BEFORE all panda3d imports
    # It must come before 'from direct.showbase.ShowBase import ShowBase'
    old_line = 'from direct.showbase.ShowBase import ShowBase'
    new_block = (
        "from panda3d.core import loadPrcFileData\n"
        "loadPrcFileData('', 'load-display p3tinydisplay')\n"
        "\n"
        "from direct.showbase.ShowBase import ShowBase"
    )
    content = content.replace(old_line, new_block, 1)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print('PATCHED')
