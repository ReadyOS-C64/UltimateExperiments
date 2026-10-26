.ifndef BCQ_PROOF_API
BCQ_PROOF_API=1
.include "cache/api.inc"
.include "render/geos/semantic.inc"
BCQ_PAGE_PROOF=BC_PAGE_PROOF
BCQP=GSEM_FRAME+29
BCQP_SOURCE=BCQP
BCQP_AUTH=BCQP+59
BCQP_CACHE=BCQP+72             ;page/genlo/genhi/kindCR
BCQP_USED=BCQP+76
BCQP_NEXT=BCQP+78
BCQP_CRC=BCQP+83
BCQP_SLOTS=BCQP+82
.assert BCQP_SLOTS<GSEM_FRAME+169,error,"CRproof overlapsINLINEhint"
.endif
