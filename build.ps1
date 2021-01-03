$env:PATH="$env:PATH;C:\Windows\System32\downlevel;C:\Program Files (x86)\NSIS"
pyinstaller --name="OBSTouchOSC" --windowed --onedir --noupx -y src\main.py
#pyinstaller --name="OBSTouchOSC" --debug all --onedir --noupx -y src\main.py
Copy-Item -Recurse "icons" ".\dist\OBSTouchOSC\"
makensis /X"SetCompressor /FINAL lzma" installer.nsis
