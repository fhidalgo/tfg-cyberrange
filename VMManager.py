#!/usr/bin/python
# Coding: utf-8

# Author: Fernando Hidalgo Paredes

# Se importan los módulos necesarios
from signal import signal, SIGINT
import proxmoxer, getpass
from proxmoxer import ProxmoxAPI
from proxmoxer.backends.https import AuthenticationError
from texttable import Texttable
from optparse import OptionParser
from consolemenu import *
from consolemenu.items import *
import yaml
import traceback
import proxmoxutils
import os

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
main_menu = ConsoleMenu("Cyberrange VM Manager", "--=oO Author: Fernando Hidalgo Paredes Oo=--", exit_option_text='Salir')

# Función para gestionar la salida del programa con Ctrl+C.
def control_c_quit():
    if opts.verbose: print("\n[!] - Se ha abortado el programa con Ctrl+C.")
    exit(1)

# Comprueba si hay una conexión activa al hipervisor Proxmox.
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
        return getpass.getpass(prompt='[i] - Introduzca la contraseña para conectarse al servidor:\n>>')
    
def connectToServer():
    # Conexión al servidor remoto Proxmox.
    global proxmox

    while connectorStatus() == 0:
        try:
            passwd = getPassword()
            proxmox = ProxmoxAPI(opts.server, user=opts.username, password=passwd, verify_ssl=False)
        except AuthenticationError:
            print('\nLa contraseña es incorrecta')
    return

# Lista las máquinas virtuales presentes en el servidor
def listVMs(type):
    if connectorStatus() == 0: connectToServer()
    print('\n')
    t = Texttable()
    t.set_cols_align(['r', 'l', 'l'])
    t.add_row(['vmid', 'Nombre', 'Estado'])

    try:
        for vm in proxmoxutils.vm_list(proxmox.nodes(opts.node).qemu.get()):
            add = False
            if type == 'vms' and not vm.template: add = True
            elif type == 'templates' and vm.template: add = True
            elif type == 'all': add = True
            if(add): t.add_row([vm.vmid, vm.name, vm.status])
        print(t.draw())
    except:
        traceback.print_exc()
    
    print('\n Pulse enter para volver')
    input()
    return

def listStorage():
    if connectorStatus() == 0: connectToServer()
    print('\n')
    
    t = Texttable()
    t.set_cols_align(['r', 'l'])
    t.add_row(['Nombre de archivo', 'Tamaño (MBytes)'])
    
    for element in proxmox.nodes(opts.node).storage('local').content.get():
        if element['format'] == 'iso':
            t.add_row([element['volid'].split('/')[1], element['size']/(1024*1024)])
    print(t.draw())
    print('\n Pulse enter para volver')
    input()
    return

def launch_lab(lab_name):
    # Clonación de VMs
    try:
        with open('.\\labs\\' + lab_name + '\\definitions\\vms.yaml', mode='r') as file:
            vms = yaml.load(file, Loader=yaml.FullLoader)

        for vm in vms['vms']:
            vm = vm['vm']
            proxmox.nodes(opts.node).qemu(vm['vmid']).clone.create(newid=vm['newid'], name=vm['name'], vmid=vm['vmid'])
    except:
        traceback.print_exc()
    finally:
        print('\n Pulse enter para volver')
        input()
    return

def mainMenu():
    global main_menu

    # Creamos los elementos del submenú para listar máquinas virtuales.
    list_vms_submenu = ConsoleMenu("Opciones de listado de máquinas virtuales")
    list_vms_submenu.append_item(FunctionItem("Listar máquinas virtuales", listVMs, ['vms']))
    list_vms_submenu.append_item(FunctionItem("Listar templates", listVMs, ['templates']))
    list_vms_submenu.append_item(FunctionItem("Listar todo", listVMs, ['all']))
    
    # Menú para lanzar laboratorios.
    launch_lab_submenu = ConsoleMenu("Lanzar laboratorio")

    for dir in next(os.walk('.\labs'))[1]:
        launch_lab_submenu.append_item(FunctionItem(dir, launch_lab, [dir]))

    # Adjuntamos los elementos al menú principal para que se muestren.
    main_menu.append_item(SubmenuItem("Ver máquinas virtuales", list_vms_submenu, main_menu))
    main_menu.append_item(FunctionItem("Ver ISOs", listStorage))
    main_menu.append_item(SubmenuItem("Lanzar laboratorios", launch_lab_submenu, main_menu))

    # Llamamos a la función para mostrar en pantalla el menú.
    main_menu.show()
    return

def main():
    # Indica a Python que ejecute la función handler() cuando se reciba Ctrl+C.
    try:
        connectToServer()

        mainMenu()
        exit(0)
    except KeyboardInterrupt:
        control_c_quit()

if __name__ == '__main__':
    main()