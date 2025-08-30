; runtime.asm - StringBuffer Runtime Library
;    .area _CODE(CODE)

PUBLIC SB_APPEND,SB_LENGTH,MUL16,DIV16

; --- SB_APPEND ---
; StringBufferに文字列を追加する
; 入力:
;   HL: StringBufferのベースアドレス
;   DE: 追加するNULL終端文字列のベースアドレス
; 破壊されるレジスタ: AF, BC, HL, DE
SB_APPEND:
    push hl
    push de

    ; DE = 書き込み先アドレスを計算 (HL + 2 + 現在の長さ)
    ld a, (hl)      ; A = MAX_CAPACITY
    inc hl
    ld c, (hl)      ; C = CURRENT_LENGTH
    inc hl          ; HL = BUFFER_START
    ld b, 0
    add hl, bc      ; HL = BUFFER_START + CURRENT_LENGTH
    ex de, hl       ; DE = 書き込み先, HL = 追加する文字列の元アドレス

    ; BC = 追加する文字列の長さを計算
    ld b, 0
    ld c, 0
.LP_LEN:
    ld a, (hl)
    or a
    jr z, .DO_APPEND
    inc c
    inc hl
    jr .LP_LEN

.DO_APPEND:
    ; TODO: 容量チェック (CURRENT_LENGTH + 追加長 <= MAX_CAPACITY)

    ; LDIRで文字列をコピー
    pop hl          ; HL = 追加する文字列の元アドレス
    ldir            ; (HL)から(DE)へBCバイト転送

    ; CURRENT_LENGTHを更新
    pop hl
    ld b, (hl)      ; B = 旧CURRENT_LENGTH
    inc hl
    add a, c        ; A = 新CURRENT_LENGTH
    ld (hl), a      ; 保存

    ret

; --- SB_LENGTH ---
; StringBufferの現在の長さを取得する
; 入力:
;   HL: StringBufferのベースアドレス
; 出力:
;   A:  現在の文字列長
SB_LENGTH:
    inc hl
    ld a, (hl)
    ret

; runtime.asm - Multiplication and Division Library

; --- MUL16 ---
; 16bit x 16bit Unsigned Multiplication
; Input:
;   HL: Multiplicand
;   DE: Multiplier
; Output:
;   DEHL: 32bit Result (DE=high, HL=low)
; Destroys: AF, BC
MUL16:
    ld b, 16
    ld a, d
    ld c, e
    ld de, 0
.mul_loop:
    srl a         ; Multiplier bit check
    rrc c
    jr nc, .no_add
    add hl, de    ; Add multiplicand to result
.no_add:
    ex de, hl     ; DE is now result, HL is multiplicand
    add hl, hl    ; Shift multiplicand left
    ex de, hl     ; Restore
    djnz .mul_loop
    ex de, hl     ; Final result in DEHL
    ret

; --- DIV16 ---
; 16bit / 16bit Unsigned Division
; Input:
;   HL: Dividend
;   DE: Divisor
; Output:
;   HL: Quotient
;   DE: Remainder
; Destroys: AF, BC
DIV16:
    ld b, 16
    ld bc, 0      ; Quotient
.div_loop:
    add hl, hl    ; Shift dividend left
    rl c
    rl b
    sbc hl, de    ; Subtract divisor
    jr nc, .no_sub
    add hl, de    ; Restore if borrow
    res 0, c      ; Clear quotient bit
.no_sub:
    djnz .div_loop
    ex de, hl     ; Remainder in DE
    ld h, b
    ld l, c       ; Quotient in HL
    ret

    END
; --- END OF FILE ---
; vim: set ts=4 sw=4 et: