# Wrapper para presentar información de una máquina virtual de Proxmox.
class ProxmoxVM:
    def __init__(self, vmid, status, name, template):
        self.vmid = vmid
        self.status = status
        self.name = name
        if template == 1:
            self.template = True
        else:
            self.template = False
            
    def to_string(self):
        dict = { 'vmid' : self.vmid,
                 'status' : self.status,
                 'name' : self.name,
                 'template' : self.template
        }
        
        return '[' + str(dict) + ']'
        
   
    def __lt__(self, other):
        return self.vmid < other.vmid


# Función que devuelve una lista de máquinas virtuales presentes en Proxmox ordenadas por vmid.
def vm_list(vmlist):
    vms = list()

    for vm in vmlist:
        vms.append(ProxmoxVM(vm['vmid'],vm['status'],vm['name'],vm['template']))
    
    vms.sort()
    
    return vms