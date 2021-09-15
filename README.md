# hass-linkstation-addon

# Overview

LinkStation Addon is a custom integration of Home Assistant to get diks infomation from Buffalo LinkStation NAS. This could display disk space available for each disk attached to Link Station including a USB disk. 

The current version tested by LinkStation Pro Duo LS-WXL. 


# Installation
- Clone this repository
- Copy `custom_components/linkstation` to your Home Assistant configuration folder. 
- Add Configration to configuration.yaml

``` yaml
linkstation:
  - name: LinkStation
    host: 192.168.1.2 # LinkStation IP Address
    username: !secret linkstation_username
    password: !secret linkstation_password
    scan_interval: 1800 # 30 mins
```
