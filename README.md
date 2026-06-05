# Desktop Finder

Windows 桌面文件搜索工具，搜索到文件后用箭头动画指向其位置。

## 功能

- 模糊搜索桌面、文档、下载目录中的文件和文件夹
- 桌面文件：红色箭头直接指向桌面图标位置
- 其他文件：自动打开所在文件夹并选中，箭头指向 Explorer 窗口
- 亮色/暗色主题切换
- 支持键盘操作（上下选择、回车确认、Esc退出）
- 窗口可拖拽

## 运行

```bash
pip install PyQt5
python main.py
```

## 打包为 exe

```bash
pip install pyinstaller
python -m PyInstaller --onefile --windowed --name "DesktopFinder" main.py
```

产物在 `dist/DesktopFinder.exe`，双击即可使用。

## 快捷键

| 按键 | 功能 |
|------|------|
| 上/下 | 选择搜索结果 |
| Enter | 确认选择 |
| Esc | 退出程序 |
