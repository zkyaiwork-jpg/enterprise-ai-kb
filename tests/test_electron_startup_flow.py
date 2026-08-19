from pathlib import Path


PROJECT_ROOT = Path(__file__).parents[1]


def test_electron_opens_main_window_before_starting_backend_health_wait():
    source = (PROJECT_ROOT / "desktop" / "main.ts").read_text(encoding="utf-8")
    startup = source[source.index("app.whenReady().then"):source.index("}).catch", source.index("app.whenReady().then"))]

    assert "createSplashWindow" not in source
    assert startup.index("await createWindow()") < startup.index("void startBackendInBackground")
    assert "await ensureBackendHealthy" not in startup


def test_electron_keeps_backend_lifecycle_management():
    source = (PROJECT_ROOT / "desktop" / "main.ts").read_text(encoding="utf-8")

    assert "startBackend(apiKey)" in source
    assert "waitForBackendHealthy()" in source
    assert "if (backendProcess && !backendProcess.killed) backendProcess.kill()" in source
    assert "app.on('before-quit', stopChildren)" in source


def test_dashboard_polls_health_and_exposes_startup_states():
    source = (PROJECT_ROOT / "frontend-react" / "src" / "pages" / "Dashboard.tsx").read_text(encoding="utf-8")

    assert "getHealth()" in source
    assert "setTimeout(() => { void pollHealth(attempt + 1) }, 1_000)" in source
    assert "AI服务启动中" in source
    assert "AI服务启动失败，请检查日志。" in source
    assert "result.status === 'healthy'" in source
