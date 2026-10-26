import Quickshell

ShellRoot {
    WindowOpacity {}
    VolumeOsd { id: volumeOsd; barPosition: desktopBar.notificationPosition }
    ScreenshotOsd {}
    SettingsWindow { id: settings }
    Notifications { id: notifications; barPosition: desktopBar.notificationPosition }
    RecorderOSD {}
    PowerMenu { id: power; barPosition: desktopBar.notificationPosition }
    Bar {
        id: desktopBar
        notificationController: notifications
        powerController: power
        volumeController: volumeOsd

    }
    Todo { id: todo }
    QuickActions { id: actions }
}
