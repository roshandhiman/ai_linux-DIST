import QtQuick
import QtMultimedia
import org.kde.plasma.plasmoid

WallpaperItem {
    id: wallpaper

    Rectangle {
        anchors.fill: parent
        color: wallpaper.configuration.Background
        clip: true

        Image {
            anchors.fill: parent
            source: wallpaper.configuration.Picture
            fillMode: Image.PreserveAspectCrop
            asynchronous: true
            visible: !video.visible
        }

        VideoOutput {
            id: video
            anchors.fill: parent
            visible: player.hasVideo && player.error === MediaPlayer.NoError
            fillMode: {
                switch (wallpaper.configuration.Fit) {
                case "fit": return VideoOutput.PreserveAspectFit
                case "stretch": return VideoOutput.Stretch
                default: return VideoOutput.PreserveAspectCrop
                }
            }
        }
    }

    MediaPlayer {
        id: player
        source: wallpaper.configuration.Video
        videoOutput: video
        loops: MediaPlayer.Infinite
        autoPlay: true
    }
}
