; Private prototype: literal current-line output certificate, never crossjob.
.ifndef SOURCE_STYLE_CERTIFICATE
SOURCE_STYLE_CERTIFICATE=1
SC_CONSUME=7               ;editorC20 only; completehit orhandnormalC26toroot
SC_VALID=$4400             ;0absent,1accumulating,2currentC20linecompleted
SC_KEY=$4401               ;59B exact frozenFSidentity, same as actualC20map
SC_START=$443C             ;3B GL_START
SC_COUNT=$443F             ;contiguous0..161 source styles/roles
SC_CONTEXT=$4440           ;10B GSEM START/END/BODY/ROLE
SC_STYLES=$444A            ;161 literal canonical source styles
SC_ROLES=$44EB             ;161 literal canonical source semantic roles
SC_END=$458C
SC_TEMP=GS_CONTROL+5       ;3B otherwiseunused9131..9133, belowparent9134
.assert SC_ROLES+161=SC_END,error,"style certificate extent"
.assert SC_END<=$45E6,error,"style certificate overlaps live continuation"
.assert SC_TEMP+3=$9134,error,"style certificate aliases parent"
.ifdef SE_EDITOR_GEOS_RENDERED
.error "literal source certificate cannot replace rendered canonical ledger"
.endif
.endif
