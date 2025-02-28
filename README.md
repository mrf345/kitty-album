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
| enter/q/ctrl+d  | Exit                 |


## Setup

#### Arch Linux:

- Install the [kitty-album](https://aur.archlinux.org/packages/kitty-album-git/) package from AUR, with your AUR helper

```bash
yay -S kitty-album-git
```

- Add it to your kitty configuration files:
    - `~/.config/kitty/kitty.conf`
        ```conf
        # Show all images in the current directory when you press Ctrl + Shift + A
        map ctrl+shift+a kitten /usr/bin/kitty-album
        ```
    
    - `~/.config/kitty/open-actions.conf`
        ```conf
        # Open any image link in kitty with kitty-album 
        protocol file
        mime image/*
        action kitten /usr/bin/kitty-album ${FILE_PATH}
        ```

Also you can use the `/usr/bin/kitty-album` command to open images from your terminal:

```bash
kitty-album ~/Pictures/test.jpg
```

#### Other Linux distros:

- Make sure you have the [kitty](https://sw.kovidgoyal.net/kitty/) and [imagemagick](https://imagemagick.org/) packages installed

- Add the source to your kitty folder:

```bash
wget https://raw.githubusercontent.com/AlvaroBernalG/kitty-album/main/album.py -O ~/.config/kitty/album.py
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
