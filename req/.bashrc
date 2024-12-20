# Custom:
wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo apt -y --fix-broken install
sudo apt-get -y install dbus-x11 xfonts-base xfonts-100dpi xfonts-75dpi xfonts-cyrillic xfonts-scalable fonts-liberation libgbm1 libvulkan1 xdg-utils
sudo dpkg -i google-chrome-stable_current_amd64.deb

pip install ipython
pip install openpyxl