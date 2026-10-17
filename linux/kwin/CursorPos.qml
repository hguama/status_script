import QtQuick
import org.kde.kwin

Item {
    id: root

    // true si desde el último envío el cursor tocó el píxel del borde. KWin lo
    // rebota 1 px mientras se empuja contra un borde reservado, así que cada
    // toque es un evento de empuje real (un cursor quieto no genera ninguno).
    property bool empuje: false

    DBusCall {
        id: cursorCall
        service: "org.statusscript.Cursor"
        path: "/Cursor"
        dbusInterface: "org.statusscript.Cursor"
        method: "pos"
    }

    DBusCall {
        id: ventanaCall
        service: "org.statusscript.Cursor"
        path: "/Cursor"
        dbusInterface: "org.statusscript.Cursor"
        method: "ventana"
    }

    // Ventana activa (clase y geometría) para utils/marca_scroll.
    Timer {
        interval: 200
        repeat: true
        running: true
        onTriggered: {
            var w = Workspace.activeWindow;
            if (!w) return;
            var g = w.frameGeometry;
            ventanaCall.arguments = [String(w.resourceClass), Math.round(g.x), Math.round(g.y),
                                     Math.round(g.width), Math.round(g.height)];
            ventanaCall.call();
        }
    }

    Connections {
        target: Workspace
        function onCursorPosChanged() {
            var p = Workspace.cursorPos;
            var s = Workspace.virtualScreenSize;
            if (p.x <= 0 || p.y <= 0 || p.x >= s.width - 1 || p.y >= s.height - 1)
                root.empuje = true;
        }
    }

    Timer {
        interval: 16
        repeat: true
        running: true
        onTriggered: {
            var p = Workspace.cursorPos;
            cursorCall.arguments = [p.x, p.y, root.empuje];
            cursorCall.call();
            root.empuje = false;
        }
    }

    // Wrap-around: reservar los cuatro bordes solo para que KWin rebote el
    // cursor (la señal de empuje de arriba). El aviso de KWin no se usa: el
    // tiempo y la intención los decide utils/wrap_around con las muestras.
    ScreenEdgeHandler { edge: ScreenEdgeHandler.LeftEdge }
    ScreenEdgeHandler { edge: ScreenEdgeHandler.RightEdge }
    ScreenEdgeHandler { edge: ScreenEdgeHandler.TopEdge }
    ScreenEdgeHandler { edge: ScreenEdgeHandler.BottomEdge }
}
