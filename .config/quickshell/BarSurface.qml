import QtQuick

// Paint each surface once. A child opacity replaces its parent surface alpha.
Item {
    id: root
    property color surfaceColor: "black"
    property real surfaceOpacity: 1
    property real radius: 0
    property var patches: []
    property var holes: []
    onSurfaceColorChanged: canvas.requestPaint()
    onSurfaceOpacityChanged: canvas.requestPaint()
    onRadiusChanged: canvas.requestPaint()
    onPatchesChanged: canvas.requestPaint()
    onHolesChanged: canvas.requestPaint()
    Canvas {
        id: canvas
        anchors.fill: parent
        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
        function rounded(ctx,x,y,w,h,r) {
            r=Math.max(0,Math.min(r,w/2,h/2));ctx.beginPath();ctx.moveTo(x+r,y);
            ctx.arcTo(x+w,y,x+w,y+h,r);ctx.arcTo(x+w,y+h,x,y+h,r);
            ctx.arcTo(x,y+h,x,y,r);ctx.arcTo(x,y,x+w,y,r);ctx.closePath();
        }
        onPaint: {
            const ctx=getContext("2d");ctx.reset();ctx.clearRect(0,0,width,height);
            rounded(ctx,0,0,width,height,root.radius);ctx.clip();
            ctx.fillStyle=Qt.rgba(root.surfaceColor.r,root.surfaceColor.g,root.surfaceColor.b,1);
            ctx.globalAlpha=Math.max(0,Math.min(1,root.surfaceOpacity));ctx.fillRect(0,0,width,height);
            for(const hole of root.holes){
                ctx.save();rounded(ctx,hole.x,hole.y,hole.width,hole.height,hole.radius||0);
                ctx.globalCompositeOperation="destination-out";ctx.globalAlpha=1;ctx.fill();ctx.restore();
            }
            for(const patch of root.patches){
                ctx.clearRect(patch.x,patch.y,patch.width,patch.height);
                ctx.globalAlpha=Math.max(0,Math.min(1,patch.opacity));ctx.fillRect(patch.x,patch.y,patch.width,patch.height);
            }
        }
    }
}
