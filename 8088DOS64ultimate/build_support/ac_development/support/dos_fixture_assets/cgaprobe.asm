; Original8088 guest COM. Genuine DOS owns loading/termination.
cpu 8086
bits 16
org 100h
start:
    mov bp,4
next_mode:
    mov ax,bp
    int 10h
    mov ax,0b800h
    mov es,ax
    mov bx,bp
    shl bx,1
    shl bx,1
    shl bx,1
    shl bx,1
    add bx,bp
    cld
    xor di,di
    mov cx,4000h
fill:
    mov ax,di
    xor al,ah
    xor al,bl
    stosb
    loop fill
    mov word [es:3ff0h],4f44h ; DO
    mov word [es:3ff2h],3653h ; S6
    mov word [es:3ff4h],4334h ; 4C
    mov word [es:3ff6h],4147h ; GA
    mov ax,bp
    mov [es:3ff8h],al
    mov byte [es:3ff9h],0a5h
    xor ax,ax
    int 16h
    inc bp
    cmp bp,7
    jl next_mode
    mov ax,3
    int 10h
    mov dx,done
    mov ah,9
    int 21h
    mov ax,4c00h
    int 21h
done: db 'DOS64 CGA COMPLETE',13,10,'$'
