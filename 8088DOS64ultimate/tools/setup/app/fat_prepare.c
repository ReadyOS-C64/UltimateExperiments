#include "fat_prepare.h"
#include "setup_io.h"
#include "selection_capsule.h"
#include "bulk_context.h"
static const nf_u32 bases[3]={0x100000UL,0x180000UL,0x380000UL};
static nf_u8 sources(void){nf_u8 i;for(i=0;i<3;i++)if(nf_source(i,bases[i],368640UL))return nf_error;return 0;}
static nf_u8 begin(nf_u8 flags,nf_u8 profile){if(!nf_inactive())return nf_error?nf_error:NF_E_STATE;if(flags<0x80||flags>0x83)return NF_E_INPUT;nf_reu_mib=4;return nf_init(profile);}
nf_u8 fp_selection(void){sq_page=1;if(sq_read()!=192)return 0;return 0x80|sq_bytes[160]|(sq_bytes[161]<<1);}
nf_u8 fp_prepare_c(nf_u8 flags){nf_u8 e;e=begin(flags,flags&1);if(e)return e;if(sources())return nf_error;if(flags&2){if(!ns_source_bind())return NF_E_IO;return nf_import_existing(bc_source_bytes());}return nf_import_dos();}
nf_u8 fp_prepare_b(nf_u8 flags){nf_u8 e;e=begin(flags,2);return e?e:nf_plan();}
nf_u8 fp_prepare_a(nf_u8 flags,nf_u16 auto_size,nf_u16 config_size){nf_u8 e;if(auto_size>8192||config_size>8192){if(!nf_inactive())return nf_error?nf_error:NF_E_STATE;return NF_E_INPUT;}e=begin(flags,0);if(e)return e;if(sources())return nf_error;return nf_derive_a(0,0x200000UL,0x3da000UL,auto_size,0x3dc000UL,config_size);}
