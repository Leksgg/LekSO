#!/usr/bin/env python3
"""Filtro seccomp del perfil --estricta de caja.sh: escribe el programa BPF en la salida estándar.

Para programas no fiables (un .exe descargado, algo sospechoso). NO es para Steam ni los juegos:
Steam crea sus propios contenedores y necesita espacios de usuario.
Bloquea lo que sirve para salir de una caja o para atacar el núcleo: crear espacios de usuario,
montar sistemas de archivos, ptrace y lectura de memoria ajena, bpf, io_uring, módulos del núcleo,
llaveros, perf y reiniciar.
Requiere el paquete python3-seccomp.
"""
import errno
import sys

import seccomp

CLONE_NEWUSER = 0x10000000
EPERM, ENOSYS = errno.EPERM, errno.ENOSYS

filtro = seccomp.SyscallFilter(defaction=seccomp.ALLOW)
for nombre in ("unshare", "setns", "mount", "umount2", "pivot_root", "chroot", "ptrace",
               "process_vm_readv", "process_vm_writev", "bpf", "userfaultfd", "perf_event_open",
               "keyctl", "add_key", "request_key", "init_module", "finit_module", "delete_module",
               "kexec_load", "kexec_file_load", "reboot", "swapon", "swapoff", "acct",
               "open_by_handle_at", "name_to_handle_at", "iopl", "ioperm", "settimeofday",
               "io_uring_setup", "io_uring_enter", "io_uring_register", "move_mount", "open_tree",
               "fsopen", "fsmount", "fspick", "mount_setattr"):
    try:
        filtro.add_rule(seccomp.ERRNO(EPERM), nombre)
    except (RuntimeError, OSError):          # la llamada no existe en este núcleo o esta libseccomp
        pass
# clone3 no deja ver sus banderas: se responde "no existe" para que glibc use clone, que sí se filtra.
filtro.add_rule(seccomp.ERRNO(ENOSYS), "clone3")
filtro.add_rule(seccomp.ERRNO(EPERM), "clone",
                seccomp.Arg(0, seccomp.MASKED_EQ, CLONE_NEWUSER, CLONE_NEWUSER))
filtro.export_bpf(sys.stdout.buffer)
