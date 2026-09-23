import QtQuick
import org.kde.kwin

Item {
    DBusCall {
        id: cursorCall
        service: "org.statusscript.Cursor"
        path: "/Cursor"
        dbusInterface: "org.statusscript.Cursor"
        method: "pos"
    }

    Timer {
        interval: 16
        repeat: true
        running: true
        onTriggered: {
            var p = Workspace.cursorPos;
            cursorCall.arguments = [p.x, p.y];
            cursorCall.call();
        }
    }
}
