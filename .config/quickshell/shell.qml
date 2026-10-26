import Quickshell

ShellRoot {
    WindowOpacity {}
    OpacityControl {id:opacityControl;barPosition:desktopBar.notificationPosition;uiScale:desktopBar.config.scale}
    VolumeOsd { id: volumeOsd; barPosition: desktopBar.notificationPosition; brightnessStep: desktopBar.config.volStep; opacityController:opacityControl }
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
        opacityController: opacityControl

    }
    Todo { id: todo }
    QuickActions { id: actions }
}
