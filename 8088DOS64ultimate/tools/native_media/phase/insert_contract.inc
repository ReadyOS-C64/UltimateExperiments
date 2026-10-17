; SETUP-independent modal Insert continuity, exclusive returned phase owner.
MI_KIND=$7fb7
MI_FQ=$7fb8
MI_LEDGER_BYTES=211
MI_READY=$7fd3
MI_VERSION=$7fd4
MI_ONLINE=$7fd5
MI_SEQUENCE=$7fd6
MI_LEDGER_CRC=$7fd8
MI_HOME_CRC=$7fdc
MI_TAIL=$7fe0
MI_ANCHORS_CRC=$7ff8
MI_CHECKSUM=$7ffc
.assert MI_CHECKSUM+4=$8000,error,"Insert receipt exact jobtail"
