const searchUrl = "file:///usr/share/applications/org.mineos.Apps.desktop";
const launchers = [
    "applications:org.mineos.Settings.desktop",
    "applications:org.kde.dolphin.desktop",
    "applications:org.mineos.Terminal.desktop",
    "applications:org.kde.discover.desktop",
    "applications:firefox-esr.desktop",
    "applications:org.mineos.Assistant.desktop"
];

const bottomPanels = panels().filter(panel => panel.location === "bottom");
if (bottomPanels.length === 0) {
    throw new Error("No bottom panel is ready");
}

for (const panel of bottomPanels) {
    const widgets = panel.widgets();
    const taskManager = widgets.find(widget => widget.type === "org.kde.plasma.icontasks");
    if (!taskManager) continue;

    const kickoff = widgets.find(widget => widget.type === "org.kde.plasma.kickoff");
    let launcher = widgets.find(widget => {
        if (widget.type !== "org.kde.plasma.icon") return false;
        widget.currentConfigGroup = ["General"];
        return widget.readConfig("url", "") === searchUrl;
    });

    if (!launcher) {
        launcher = panel.addWidget("org.kde.plasma.icon");
        launcher.currentConfigGroup = ["General"];
        launcher.writeConfig("url", searchUrl);
    }
    launcher.globalShortcut = "Meta+Space";
    if (kickoff) kickoff.remove();

    taskManager.currentConfigGroup = ["General"];
    taskManager.writeConfig("launchers", launchers.join(","));
    taskManager.reloadConfig();
    print(String(panel.id) + " " + String(launcher.id));
}
