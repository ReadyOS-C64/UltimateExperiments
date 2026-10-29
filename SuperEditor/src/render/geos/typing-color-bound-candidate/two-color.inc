; Private exact election helper. Caller first authenticates full GCC/GTC/source
; and owned FE/font capability via normal R30 admission/current guard.
; A0/Cclear permits unchanged tile attributes; A2/Cclear declines. Provider
; errors preserve carry. Owner!=4 returns B2/Cset before touching the frame.
TCB_FRAME=$8A00
TCB_ROW=0
TCB_TOP=1
TCB_FIRST=2 ;inclusive changed tile column
TCB_LAST=3  ;inclusive max(old,new)-1 tile column
TCB_ATTR=4  ;target role0/background6 declaration, exactly16hex
TCB_SIZE=40 ;five inputs, private work,16pixelrow owners
TCB_BASE=$8400 ;360 provisional caret-free target INK bytes (flags0)
TCB_VOTES=$8580 ;80 white votes; yellow votes85D0..861F
TCB_HEADER=$90CA ;authenticated original64B header, preserved
TCB_ROLEBUF=$8200 ;161 role bytes, then161 sourcechars
; Scratch:8000..833F (full2band640B snapshot, prefix,chars,styles),
; 8580..861F (votes),8640..8783 (162 Xwords), existingforeground ZP,
; GP_IO9178..917D and the existing checked-DMA requests. No BSS/ZP allocation.
