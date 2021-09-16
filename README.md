# hass-linkstation-addon

# Overview

LinkStation Addon is a custom integration of Home Assistant to get disks infomation from Buffalo LinkStation NAS. This could display disk space available for each disk attached to Link Station including a USB disk. 

The current version tested by LinkStation Pro Duo LS-WXL. 

# Features

## Sensors (for each disk)
- Disk status (normal, remove)
- Disk space used (%)
- Disk space available (GB)

## Services
- Refresh status
- Restart LinkStation (coming soon)

# Installation
- Clone this repository
- Copy `custom_components/linkstation` to your Home Assistant configuration folder. 
- Add Configration to configuration.yaml

``` yaml
linkstation:
    name: LinkStation
    host: 192.168.1.2 # LinkStation IP Address
    username: !secret linkstation_username
    password: !secret linkstation_password
    scan_interval: 1800 # 30 mins
```

# Screenshot
![ui entities screenshot](/docs/screenshot-entities-ui.png)
![configuration sceenshot](/docs/screenshot-configuration.png)
