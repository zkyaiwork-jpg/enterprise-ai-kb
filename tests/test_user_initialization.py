from pathlib import Path


PROJECT_ROOT = Path(__file__).parents[1]


def test_electron_routes_new_user_to_welcome_and_keeps_user_ipc_private():
    main_source = (PROJECT_ROOT / "desktop" / "main.ts").read_text(encoding="utf-8")

    assert "settings.user_name" in main_source
    assert "`${devUrl}/welcome`" in main_source
    assert "`${frontendUrl}/welcome`" in main_source
    user_info_handler = main_source[
        main_source.index("ipcMain.handle('settings:get-user-info'"):
        main_source.index("ipcMain.handle('settings:save-user-name'")
    ]
    assert "userName: settings.user_name" in user_info_handler
    assert "deepseek_api_key" not in user_info_handler


def test_react_uses_dynamic_user_name_without_hardcoded_job_title():
    top_bar = (PROJECT_ROOT / "frontend-react" / "src" / "components" / "TopBar.tsx").read_text(encoding="utf-8")
    hero = (PROJECT_ROOT / "frontend-react" / "src" / "components" / "dashboard" / "HeroCard.tsx").read_text(encoding="utf-8")
    welcome = (PROJECT_ROOT / "frontend-react" / "src" / "pages" / "Welcome.tsx").read_text(encoding="utf-8")

    assert "displayName" in top_bar
    assert "张伟" not in top_bar
    assert "产品经理" not in top_bar
    assert "你好，{userName} 👋" in hero
    assert "saveUserName" in welcome
    assert "navigate('/', { replace: true })" in welcome
