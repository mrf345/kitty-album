<h1 align="center">
    kitty-album
</h1>

<p align="center">
  <img src="./assets/demo.gif" alt="demo"/>
</p>


## Usage

| Key binding     | Action               |
|-----------------|----------------------|
| left arrow      | Go to previous image |
| right arrow     | Go to next image     |
| end key         | Go to last image     |
| home key        | Go to first image    |
| = key           | Zoom in              |
| - key           | Zoom out             |
| enter/q/ctrl+d  | Exit                 |


## Setup

### Arch Linux:

- Install the [kitty-album](https://aur.archlinux.org/packages/kitty-album-git/) package from AUR, with your helper of choice:

```bash
yay -S kitty-album-git
```

- Add it to your kitty configuration files:
    - `~/.config/kitty/kitty.conf`
        ```conf
        # Show all images in the current directory when you press Ctrl + Shift + A
        map ctrl+shift+a kitten /usr/bin/kitty_album.py
        ```
    
    - `~/.config/kitty/open-actions.conf`
        ```conf
        # Open any image link in kitty with kitty-album 
        protocol file
        mime image/*
        action kitten /usr/bin/kitty_album.py ${FILE_PATH}
        ```

Also you can use the `/usr/bin/kitty_album.py` command to open images from kitty:

```bash
kitty_album.py ~/Pictures/test.jpg
```

### Other Linux distros:

- Make sure you have the [kitty](https://github.com/kovidgoyal/kitty/) and [imagemagick](https://github.com/ImageMagick/ImageMagick) packages installed

- Add the source to your kitty folder:

```bash
wget https://raw.githubusercontent.com/mrf345/kitty-album/master/album.py -O ~/.config/kitty/album.py
```

- Add it to your kitty configuration files:
    - `~/.config/kitty/kitty.conf`
        ```conf
        # Show all images in the current directory when you press Ctrl + Shift + A
        map ctrl+shift+a kitten album.py
        ```
    
    - `~/.config/kitty/open-actions.conf`
        ```conf
        # Open any image link in kitty with kitty-album 
        protocol file
        mime image/*
        action kitten album.py ${FILE_PATH}
        ```
