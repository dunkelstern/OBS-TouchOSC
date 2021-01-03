PYTHON_VERSION=$(python -V|sed -e 's/Python \([0-9]*\.[0-9]*\)\..*/\1/')
export PYTHONOPTIMIZE=1

if [ "$1" = "" ] ; then
    MODE='--onefile'
else
    MODE="$1"
fi

pyinstaller \
    --name="OBSTouchOSC" \
    --add-data "icons/play.png:icons" \
    --add-data "icons/play@2x.png:icons" \
    --add-data "icons/stop.png:icons" \
    --add-data "icons/stop@2x.png:icons" \
    $MODE \
    --noupx \
    -y src/main.py
