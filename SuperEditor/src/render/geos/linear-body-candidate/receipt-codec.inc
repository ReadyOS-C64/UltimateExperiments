; Bounded actual-parser receipt codec, no source parse or new persistent state.
ECR_BATCH=$8ECA
ECR_NEXT=$8ECB
ECR_TEMP=$8ECC             ;10B input/record bounce; caller-private dead fields
ECR_LIMIT=$8ED6            ;3B checkedendpoint arithmetic
ECR_END=$8ED9             ;15Btotal through8ED8, below realFS8EE0
ECR_DATA=$9096            ;8x10B, deadGS_OVERLAP while C26 owns continuation
ECR_BODY=$8E8B            ;existing GI_BODY
ECR_BODY_END=$8E8E        ;existing GI_END
.assert ECR_END<=$8EE0,error,"receipt scratch overlaps sourceframe"
.assert ECR_DATA+80<=$90EC,error,"receipt batch overlaps native sourcepacket"
