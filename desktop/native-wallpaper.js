for (const desktop of desktops()) {
    const previous = desktop.wallpaperPlugin;
    desktop.currentConfigGroup = ["Wallpaper", previous, "General"];
    if (settings.live) {
        const existing = previous === settings.plugin;
        const restoredPlugin = existing ? desktop.readConfig("PreviousWallpaper", "org.kde.image") : previous;
        const currentPicture = desktop.readConfig(existing ? "Picture" : "Image", "");
        desktop.currentConfigGroup = ["Wallpaper", settings.plugin, "General"];
        desktop.writeConfig("PreviousWallpaper", restoredPlugin);
        desktop.writeConfig("Picture", settings.pictureChanged ? settings.picture : currentPicture || settings.picture);
        desktop.writeConfig("Background", settings.color);
        desktop.writeConfig("Fit", settings.fit);
        desktop.writeConfig("Video", settings.video);
        if (!existing) desktop.wallpaperPlugin = settings.plugin;
        if (desktop.wallpaperPlugin !== settings.plugin) throw new Error("Could not load the video wallpaper.");
        desktop.reloadConfig();
    } else if (settings.pictureChanged) {
        const plugin = settings.picture ? "org.kde.image" : "org.kde.color";
        desktop.currentConfigGroup = ["Wallpaper", plugin, "General"];
        if (settings.picture) {
            desktop.writeConfig("Image", settings.picture);
            desktop.writeConfig("FillMode", settings.pictureFit);
        }
        desktop.writeConfig("Color", settings.color);
        desktop.wallpaperPlugin = plugin;
        desktop.reloadConfig();
    } else if (previous === settings.plugin) {
        desktop.wallpaperPlugin = desktop.readConfig("PreviousWallpaper", "org.kde.image");
    }
}
print("ok");
