cpu 8086
bits 16
org 100h
; Private DOS reference fixture generator; all IO uses genuine DOS INT 21h.
; 4097 blocks x 4096 bytes. Each little-endian word = A55Ah XOR block XOR word.
start:
 mov dx,path
 xor cx,cx
 mov ah,3Ch
 int 21h
 jc fail
 mov bx,ax
 xor si,si
.writeblock:
 xor di,di
.fill:
 mov ax,si
 xor ax,di
 xor ax,0A55Ah
 shl di,1
 mov [buffer+di],ax
 shr di,1
 inc di
 cmp di,2048
 jne .fill
 mov dx,buffer
 mov cx,4096
 mov ah,40h
 int 21h
 jc failclose
 cmp ax,4096
 jne failclose
 inc si
 cmp si,4097
 jne .writeblock
 mov ah,3Eh
 int 21h
 jc fail
 mov dx,path
 mov ax,3D00h
 int 21h
 jc fail
 mov bx,ax
 xor si,si
.readblock:
 mov dx,buffer
 mov cx,4096
 mov ah,3Fh
 int 21h
 jc failclose
 cmp ax,4096
 jne failclose
 xor di,di
.check:
 mov ax,si
 xor ax,di
 xor ax,0A55Ah
 shl di,1
 cmp [buffer+di],ax
 jne failclose
 shr di,1
 inc di
 cmp di,2048
 jne .check
 inc si
 cmp si,4097
 jne .readblock
 mov dx,buffer
 mov cx,1
 mov ah,3Fh
 int 21h
 jc failclose
 or ax,ax
 jne failclose
 mov ah,3Eh
 int 21h
 jc fail
 mov dx,marker
 xor cx,cx
 mov ah,3Ch
 int 21h
 jc fail
 mov bx,ax
 mov dx,success
 mov cx,success_end-success
 mov ah,40h
 int 21h
 jc failclose
 cmp ax,success_end-success
 jne failclose
 mov ah,3Eh
 int 21h
 jc fail
 mov ax,4C00h
 int 21h
failclose:
 mov ah,3Eh
 int 21h
fail:
 mov ax,4C01h
 int 21h
path: db 'C:\CROSS16.BIN',0
marker: db 'A:\CROSS.OK',0
success: db 'DOS64_CROSS16_OK',13,10
success_end:
align 2
buffer: times 4096 db 0
