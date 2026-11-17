import QtCore
import QtQuick
import QtQuick.Controls as Controls
import QtQuick.Dialogs
import org.kde.kirigami as Kirigami

Kirigami.FormLayout {
    id: root
    twinFormLayouts: parentLayout

    property alias formLayout: root
    property string cfg_Video: ""
    property string cfg_Fit: "fill"
    readonly property var fitModes: ["fill", "fit", "stretch"]

    Controls.Button {
        Kirigami.FormData.label: "Video"
        text: root.cfg_Video ? decodeURIComponent(root.cfg_Video.split("/").pop()) : "Choose video…"
        onClicked: picker.open()
    }

    Controls.ComboBox {
        Kirigami.FormData.label: "Video fit"
        model: ["Fill screen", "Fit entire video", "Stretch"]
        currentIndex: Math.max(0, root.fitModes.indexOf(root.cfg_Fit))
        onActivated: root.cfg_Fit = root.fitModes[currentIndex]
    }

    FileDialog {
        id: picker
        title: "Choose live wallpaper"
        currentFolder: StandardPaths.writableLocation(StandardPaths.HomeLocation) + "/Wallpapers"
        nameFilters: ["Video files (*.mp4 *.webm *.mov *.mkv)", "All files (*)"]
        onAccepted: root.cfg_Video = selectedFile.toString()
    }
}
