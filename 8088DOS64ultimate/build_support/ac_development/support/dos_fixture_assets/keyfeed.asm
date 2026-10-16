cpu 8086
bits 16
org 100h
start:
 mov ax,3521h
 int 21h
 mov [old],bx
 mov [old+2],es
 mov dx,hook
 mov ax,2521h
 int 21h
 mov dx,(resident_end-$$+100h+15)/16
 mov ax,3100h
 int 21h
old: dd 0
pos: dw 0
keys: db '1',13,'1',13,'Y',13,' ',13
keys_end:
hook:
 cmp ah,0Ch
 je read
 cmp ah,08h
 je read
 jmp far [cs:old]
read:
 call snapshot
 push bx
 mov bx,[cs:pos]
 cmp bx,keys_end-keys
 jae exhausted
 mov al,[cs:keys+bx]
 nop
 inc bx
 mov [cs:pos],bx
 pop bx
 iret
exhausted:
 pop bx
 jmp far [cs:old]
snapshot:
 push ax
 push bx
 push cx
 push dx
 push ds
 push cs
 pop ds
 mov dx,name
 xor cx,cx
 mov ah,3Ch
 pushf
 call far [cs:old]
 jc .done
 mov bx,ax
 push ds
 mov ax,0B800h
 mov ds,ax
 xor dx,dx
 mov cx,4000
 mov ah,40h
 pushf
 call far [cs:old]
 pop ds
 mov ah,3Eh
 pushf
 call far [cs:old]
 inc byte [name+4]
.done:
 pop ds
 pop dx
 pop cx
 pop bx
 pop ax
 ret
name: db 'A:\S0.BIN',0
resident_end:
