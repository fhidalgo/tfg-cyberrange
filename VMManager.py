#!/usr/bin/python
# Coding: utf-8

# Author: Fernando Hidalgo Paredes

import proxmoxer, getpass
from proxmoxer import ProxmoxAPI

proxmox_host = 'proxmox.cyberrange.rew31'

def main():
    username = input("Usuario: ")
    passwd = getpass.getpass()
    proxmox = ProxmoxAPI(proxmox_host, user=username, password=passwd, verify_ssl=False)

    for node in proxmox.nodes.get():
        print(node['node'])
        for vm in proxmox.nodes(node['node']).qemu.get():
            print("{0}. {1} => {2}" .format(vm['vmid'], vm['name'], vm['status']))


if __name__ == '__main__':
    main()
