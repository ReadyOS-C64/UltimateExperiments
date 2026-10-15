; Independent guest IRQ0 test fixture; not the synthetic native BIOS handler.
; Reproduce with: nasm -f bin tests/fixtures/guest_timer.asm -o <scratch-output>
; Compare byte-for-byte with tests/host/guest_timer.bin before replacement.
CPU 8086
BITS 16
ORG 0
sti
push ds
push ax
mov ax,0x40
mov ds,ax
inc word [0x6c]
jnz check_midnight
inc word [0x6e]
check_midnight:
cmp word [0x6e],0x18
jne chain
cmp word [0x6c],0x00b0
jne chain
xor ax,ax
mov [0x6c],ax
mov [0x6e],ax
mov byte [0x70],1
chain:
int 0x1c
mov al,0x20
out 0x20,al
pop ax
pop ds
iret
