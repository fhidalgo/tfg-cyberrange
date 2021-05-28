#!/usr/bin/python
# Coding: utf-8

# Author: Fernando Hidalgo Paredes

# Se importan los módulos necesarios
from signal import signal, SIGINT
import proxmoxer, getpass
from proxmoxer import ProxmoxAPI
from texttable import Texttable
from optparse import OptionParser
from consolemenu import *
from consolemenu.items import *

# El parseador de opciones configura las diferentes opciones que el usuario puede incluir en la ejecución del script.
options = OptionParser(usage='%prog [opciones]', description='Gestiona el despliegue de máquinas virtuales en el ciberrange')

options.add_option('-s', '--server', type='str', default='proxmox.cyberrange.rew31', help='Usuario de conexión al servidor (default: root@pam)')
options.add_option('-u', '--username', type='str', default='root@pam', help='Usuario de conexión al servidor (default: root@pam)')
options.add_option('-p', '--password', type='str', help='Contraseña')
options.add_option('-v', '--verbose', action='store_true', dest='verbose', help='Ofrece más información de la ejecución del programa')
options.add_option('-n', '--node', type='str', default='cyberrange', help='Nodo dentro del servidor al que desea conectarse')

opts, args = options.parse_args()

# Declaramos el conector de Proxmox como variable global inicializado a None para controlar el estado de la conexión.
proxmox = None

# Create the menu
main_menu = ConsoleMenu("Cyberrange VM Manager", "--=oO Author: Fernando Hidalgo Paredes Oo=--")

# Función para gestionar la salida del programa con Ctrl+C.
def handler(signum, frame):
    if opts.verbose: print("\n[!] - Se ha abandonado el programa con Ctrl+C.")
    exit(1)

# Lista las máquinas virtuales presentes en el servidor
def listVMs(type):
    print('\n')
    t = Texttable()
    t.set_cols_align(['r', 'l', 'l'])
    t.add_row(['vmid', 'Nombre', 'Estado'])
    for vm in proxmox.nodes(opts.node).qemu.get():
        if type == 'vms':
            if vm['template'] != 1:
                t.add_row([vm['vmid'], vm['name'], vm['status']])
        elif type == 'templates':
            if vm['template'] == 1:
                t.add_row([vm['vmid'], vm['name'], vm['status']])
        elif type == 'all':
            t.add_row([vm['vmid'], vm['name'], vm['status']])
    print(t.draw())
    
    print('\n Pulse enter para volver')
    input()
    return

def connectorStatus():
    if proxmox is None:
        return 0
    elif proxmox.get_tokens():
        return 1
    else:
        return 2

def getPassword():
    if opts.password:
        return opts.password
    else:
        return getpass.getpass()
    
def connectToServer():
    # Conexión al servidor remoto Proxmox.
    global proxmox
    passwd = getPassword()
    proxmox = ProxmoxAPI(opts.server, user=opts.username, password=passwd, verify_ssl=False)

def mainMenu():
    global main_menu

    # Creamos los elementos del submenú para listar máquinas virtuales.
    list_vms_item = FunctionItem("Listar máquinas virtuales", listVMs, ['vms'])
    list_vms_item2 = FunctionItem("Listar templates", listVMs, ['templates'])
    list_vms_item3 = FunctionItem("Listar todo", listVMs, ['all'])
    list_vms_submenu = ConsoleMenu("Opciones de listado de máquinas virtuales")
    list_vms_submenu.append_item(list_vms_item)
    list_vms_submenu.append_item(list_vms_item2)
    list_vms_submenu.append_item(list_vms_item3)
    list_vms_submenu_item = SubmenuItem("Listar máquinas virtuales", list_vms_submenu, main_menu)
    
    # Creamos los elementos del menú principal.

    # Adjuntamos los elementos al menú principal para que se muestren.
    main_menu.append_item(list_vms_submenu_item)

    # Llamamos a la función para mostrar en pantalla el menú.
    main_menu.show()
    return

def main():
    # Indica a Python que ejecute la función handler() cuando se reciba Ctrl+C.
    signal(SIGINT, handler)
    
    connectToServer()

    mainMenu()

if __name__ == '__main__':
    main()