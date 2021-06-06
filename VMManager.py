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
import ansible_runner
import yaml
import traceback
import proxmoxutils
import os
import time
import shutil

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

# Si no se proporciona una contraseña en los argumentos, se solicitará por consola.
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
    
    print('\nPulse enter para volver')
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
    print('\nPulse enter para volver')
    input()
    return

# Borra las máquinas de un laboratorio a partir de los ficheros de configuración contenidos en la carpeta del mismo nombre.
def delete_lab(lab_name):
    try:
        errors = 0
        changes = 0
        # Rutas de directorios
        sourcepath = os.path.relpath('labs')
        # Ruta del fichero de definiciones de VMs
        vmspath = os.path.join(sourcepath, lab_name, 'definitions', 'vms.yaml')

        print('\n[!] - Comienza la destrucción del laboratorio:', lab_name)

        with open(vmspath, mode='r') as file:
            vms = yaml.load(file, Loader=yaml.FullLoader)

        print('\n[!] - Borrado de máquinas virtuales:')
        for delvm in vms['vms']:
            delvm = delvm['vm']
            vm = proxmoxutils.get_vm(proxmox.nodes(opts.node).qemu.get(), delvm['newid'])
            if vm is None:
                print('\n[x] - No puede eliminarse la máquina', delvm['name'], 'porque no existe en el servidor.')
                errors = errors + 1
            else:
                running = 0
                if proxmoxutils.get_vm(proxmox.nodes(opts.node).qemu.get(), delvm['newid']).status == 'running':
                    running = 1
                    for i in range(3):
                        print('\n[!] - Apagando máquina:', delvm['name'], '. Intento',i+1, 'de 3.')
                        proxmox.nodes(opts.node).qemu(delvm['newid']).status.shutdown.post(forceStop='1')
                        for j in range(30):
                            time.sleep(1)
                            if proxmoxutils.get_vm(proxmox.nodes(opts.node).qemu.get(), delvm['newid']).status == 'stopped':
                                running = 0
                                break
                        if running == 0:
                            break
                if running == 0:
                    print('\n[!] - Eliminando máquina:', delvm['name'])
                    proxmox.nodes(opts.node).qemu(delvm['newid']).delete(purge='1')
                    time.sleep(5)
                    if proxmoxutils.get_vm(proxmox.nodes(opts.node).qemu.get(), delvm['newid']) is None:
                        print('\n[!] - La máquina', delvm['name'], 'ha sido eliminada con éxito')
                        changes = changes + 1
                    else:
                        print('\n[x] - No pudo eliminarse la máquina', delvm['name'])
                        errors = errors + 1
                else:
                    print('\n[x] - No se pudo detener la máquina:', delvm['name'])
                    errors = errors + 1
    except:
        traceback.print_exc()
        errors = errors + 1
    finally:
        if errors > 0:
            print('\n[!] - Ha finalizado la destrucción del laboratorio con errores')
        else:
            print('\n[!] - Ha finalizado la destrucción del laboratorio correctamente. Se han borrado', changes, 'máquinas.')
        print('\nPulse enter para volver')
        input()
    return


# Lanza un laboratorio a partir de los ficheros de configuración contenidos en la carpeta del mismo nombre.
def launch_lab(lab_name):
    # Clonación de VMs
    try:
        errors = 0
        # Rutas de directorios
        sourcepath = os.path.relpath('labs')

        # Ruta del fichero de inventario de Ansible
        inventorypath = os.path.join(sourcepath, lab_name, 'inventory', 'hosts')

        # Ruta del fichero de definiciones de VMs
        vmspath = os.path.join(sourcepath, lab_name, 'definitions', 'vms.yaml')

        print('\n[!] - Comienza el despliegue del laboratorio:', lab_name) 
                    
        with open(vmspath, mode='r') as file:
            vms = yaml.load(file, Loader=yaml.FullLoader)

        print('\n[!] - Clonado de máquinas virtuales:')
        for newvm in vms['vms']:
            newvm = newvm['vm']

            vm = proxmoxutils.get_vm(proxmox.nodes(opts.node).qemu.get(), newvm['vmid'])
            if vm is None:
                print('\n[x] - No puede clonarse la máquina', newvm['name'], 'a partir de la máquina base', newvm['vmid'], 'porque no existe en el servidor.')
                errors = errors + 1
            else:
                if vm.template != 1:
                    print('\n[x] - No puede clonarse la máquina', newvm['name'], 'a partir de la máquina base', newvm['vmid'], 'porque no es un template.')
                    errors = errors + 1
                else:
                    print('\n[!] - Clonando la máquina virtual', newvm['name'])
                    proxmox.nodes(opts.node).qemu(newvm['vmid']).clone.create(newid=newvm['newid'], name=newvm['name'], vmid=newvm['vmid'])
                    time.sleep(5)

                    running = 0
                    for i in range(3):
                        print('\n[!] - Esperando que la máquina', newvm['name'],'se inicie. Intento:', i+1)
                        proxmox.nodes(opts.node).qemu(newvm['newid']).status.start.post()
                        for j in range(5):
                            time.sleep(1)
                            if proxmoxutils.get_vm(proxmox.nodes(opts.node).qemu.get(), newvm['newid']).status == 'running':
                                running = 1
                                break
                        if running == 1: break
                    if running == 0:
                        print('\n[x] - No pudo iniciarse la máquina', newvm['name'], '. No se ejecutará el plabook de Ansible para su configuración.')
                        errors = errors + 1
                    else:
                        playbookname = newvm['name'] + '.yaml'
                        playbookpath = os.path.join(sourcepath, lab_name, 'project', playbookname)
                        if os.path.exists(playbookpath):
                            print('\n[!] - La máquina', newvm['name'], 'se ha desplegado con éxito. Ejecutando playbook de Ansible...')
                            time.sleep(30)
                            r = ansible_runner.run(private_data_dir=os.path.join(sourcepath, lab_name), playbook=playbookname)
                            print(r.stats)
                        else:
                            print('\n[!] - No existe playbook de Ansible para la máquina', newvm['name'], '. Se omite este paso')
        # Limpieza del directorio 'artifacts'
        artifactspath = os.path.join(sourcepath, lab_name, 'artifacts')
        if os.path.exists(artifactspath): 
            shutil.rmtree(artifactspath)
    except:
        traceback.print_exc()
        errors = errors + 1
    finally:
        if errors > 0:
            print('\n[!] - Ha finalizado la ejecución del laboratorio con errores')
        else:
            print('\n[!] - Ha finalizado la ejecución del laboratorio correctamente')
        print('\nPulse enter para volver')
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

    # Menú para borrar laboratorios.
    delete_lab_submenu = ConsoleMenu("Destruir laboratorio")

    for dir in next(os.walk(os.path.relpath('labs')))[1]:
        launch_lab_submenu.append_item(FunctionItem(dir, launch_lab, [dir]))
        delete_lab_submenu.append_item(FunctionItem(dir, delete_lab, [dir]))

    # Adjuntamos los elementos al menú principal para que se muestren.
    main_menu.append_item(SubmenuItem("Ver máquinas virtuales", list_vms_submenu, main_menu))
    main_menu.append_item(FunctionItem("Ver ISOs", listStorage))
    main_menu.append_item(SubmenuItem("Lanzar laboratorios", launch_lab_submenu, main_menu))
    main_menu.append_item(SubmenuItem("Destruir laboratorios", delete_lab_submenu, main_menu))

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
