from pathlib import Path


PROJECT_ROOT = Path(__file__).parents[1]


def test_electron_uses_light_hidden_title_bar_and_removes_default_menu():
    main_source = (PROJECT_ROOT / "desktop" / "main.ts").read_text(encoding="utf-8")

    assert "Menu.setApplicationMenu(null)" in main_source
    assert "autoHideMenuBar: true" in main_source
    assert "titleBarStyle: 'hidden'" in main_source
    assert "color: '#F5F7FB'" in main_source
    assert "symbolColor: '#475569'" in main_source
    assert "height: 40" in main_source
    assert "mainWindow.setMenuBarVisibility(false)" in main_source


def test_desktop_title_bar_is_blank_draggable_shell_with_native_controls():
    title_bar = (
        PROJECT_ROOT
        / "frontend-react"
        / "src"
        / "components"
        / "DesktopTitleBar.tsx"
    ).read_text(encoding="utf-8")
    styles = (
        PROJECT_ROOT / "frontend-react" / "src" / "styles" / "index.css"
    ).read_text(encoding="utf-8")

    assert "企业AI知识库助手" not in title_bar
    assert "desktop-title-bar-drag-region" in title_bar
    assert "-webkit-app-region: drag" in styles
    assert "background: #f5f7fb" in styles
    assert "width: calc(100% - 144px)" in styles
