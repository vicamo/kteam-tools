#      Kernel testing using VMs

Step 1. Get a cloud image:
```
uvt-simplestreams-libvirt --verbose sync --source http://cloud-images.ubuntu.com/daily release=${RELEASE} arch=${ARCH}
```
Where:
```
 "RELEASE" is xenial, bionic, disco, etc
 "ARCH" is i386, amd64, etc. (normally run just amd64 for x86-64 testing)
```

Step 2. Spin up an instance on your host:
```
uvt-kvm create --cpu ${CPUS} --memory ${VM_MEM_SIZE} ${VM} release=${RELEASE} arch=${ARCH} --disk ${VM_HDD_SIZE} --unsafe-caching
```

Where:
```
  "CPUS" = number of CPUs you want
  "VM_MEM_SIZE" = memory size ib MB
  "VM" = a name you want to call your VM
  "RELEASE" = xenial, bioic, etc
  "ARCH" = the guest arch
  "VM_HDD_SIZE" = the size of the VM disc in GB (Note: min size is 3GB)
```

Step 3. You can see the list of running VMs using:
```
uvt-kvm list
```

Step 4. You can destroy them using:
```
uvt-kvm destroy ${VM}
```

Step 5. You can wait for the VM to deploy using:
```
uvt-kvm wait ${VM}
```

Step 6. Get the local IP of a target VM using:
```
uvt-kvm ip ${VM}
```

Step 7. You can ssh into a VM using:
```
uvt-kvm ssh --insecure ${VM}
```

Or directly using ssh:
```
IP=$(uvt-kvm ip ${VM})
ssh ubuntu@${IP}
```

Step 8. Get serial console of a VM:
```
virsh console ${VM}
```

Step 10. Force virsh to totally forget the VM (if it gets totally messed up):
```
uvt-kvm destroy ${VM}
virsh undefine ${VM}
```
