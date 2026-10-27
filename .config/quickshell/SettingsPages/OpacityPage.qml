import QtQuick
import QtQuick.Controls
import Quickshell
import "../"
Item {
    id:page
    property real marginLeft:0
    property real marginRight:10
    property real marginTop:0
    property real marginBottom:0
    property var opacityController:null
    onOpacityControllerChanged:if(opacityController)opacityController.prepareOsd()
    Connections {target:page.opacityController
        function onOsdAvailableChanged(){if(page.opacityController&&!page.opacityController.osdAvailable)page.opacityController.prepareOsd();}
        function onOsdPercentChanged(){workspaceSlider.value=(page.opacityController.osdPercent-40)/60;}
    }
    Flickable {
        anchors.fill:parent;clip:true;contentHeight:content.implicitHeight
        Column {
            id:content;width:parent.width;spacing:18
            Text {text:LocaleState.tr("OPACITÉ DES FENÊTRES","WINDOW OPACITY");font.family:Theme.fontFamily;font.pixelSize:Theme.textSizeSection;font.bold:true;color:Theme.text}
            Rectangle {
                width:parent.width;height:132;radius:Theme.radius;color:"transparent";border.width:1;border.color:Theme.border
                Column {anchors.fill:parent;anchors.margins:14;spacing:14
                    Text {text:LocaleState.tr("Bureau actuel","Current workspace");font.family:Theme.fontFamily;color:Theme.text;font.pixelSize:Theme.textSizeGroup}
                    Slider {id:workspaceSlider;width:parent.width;icon:"󰗌";resettable:true;resetValue:0;step:1/60;displayFrom:40;displayTo:100
                        enabled:!!page.opacityController&&page.opacityController.osdAvailable
                        value:page.opacityController?(page.opacityController.osdPercent-40)/60:1
                        displayText:page.opacityController?page.opacityController.osdPercent+"%":"—"
                        onMoved:value=>{if(page.opacityController)page.opacityController.setOsdPercent(40+Math.round(value*60));}
                    }
                    Text {text:LocaleState.tr("Le plein écran reste toujours opaque.","Fullscreen always stays opaque.");color:Theme.textDim;font.pixelSize:Theme.textSizeSmall}
                }
            }
            Text {width:parent.width;wrapMode:Text.WordWrap;text:LocaleState.tr("Super+O : bureau. Super+Maj+O : fenêtre sélectionnée. Molette : pas de 1 %. Clic droit du module : retirer toutes les exceptions.","Super+O: workspace. Super+Shift+O: selected window. Wheel: 1% steps. Right-click the module to remove all overrides.");color:Theme.textDim;font.family:Theme.fontFamily;font.pixelSize:Theme.textSizeBody}
            Text {width:parent.width;wrapMode:Text.WordWrap;text:LocaleState.tr("Bulles : maintenir un bouton ou le fond du groupe, puis utiliser la molette. Le groupe règle son fond et tous ses boutons ; un bouton peut ensuite recevoir une valeur distincte.","Bubbles: hold a button or the group background, then scroll. A group changes its background and all its buttons; each button may then have its own value.");color:Theme.textDim;font.family:Theme.fontFamily;font.pixelSize:Theme.textSizeBody}
            Rectangle {width:parent.width;height:36;radius:Theme.radius;color:Theme.alpha(Theme.accent,0.1);border.width:1;border.color:Theme.border
                Text {anchors.centerIn:parent;text:LocaleState.tr("Rétablir l’opacité de tous les boutons et bulles","Restore all buttons and bubbles to full opacity");color:Theme.text;font.family:Theme.fontFamily;font.pixelSize:Theme.textSizeSmall}
                MouseArea {anchors.fill:parent;onClicked:Quickshell.execDetached(["qs","ipc","call","bar","resetOpacities"])}
            }
        }
    }
}
